from decimal import Decimal, ROUND_DOWN, ROUND_UP
from uuid import uuid4

from flask import current_app

from app.extensions import db
from app.models import LLMUsageRecord, RechargeOrder, WalletAccount, WalletLedger


class InsufficientBalanceError(Exception):
    pass


def _decimal_config(name, default):
    raw = current_app.config.get(name, default)
    return Decimal(str(raw))


def make_order_no(prefix='RC'):
    return f'{prefix}{uuid4().hex[:24].upper()}'


def make_request_id(prefix='REQ'):
    return f'{prefix}{uuid4().hex[:24].upper()}'


def make_call_id(prefix='CALL'):
    return f'{prefix}{uuid4().hex[:24].upper()}'


def coins_for_tokens(total_tokens):
    total = max(int(total_tokens or 0), 0)
    if total == 0:
        return 0
    ratio = _decimal_config('COINS_PER_1000_TOKENS', '1')
    return int((Decimal(total) * ratio / Decimal('1000')).quantize(Decimal('1'), rounding=ROUND_UP))


def max_tokens_for_coins(coins):
    total_coins = max(int(coins or 0), 0)
    if total_coins == 0:
        return 0
    ratio = _decimal_config('COINS_PER_1000_TOKENS', '1')
    if ratio <= 0:
        return 0
    return int((Decimal(total_coins) * Decimal('1000') / ratio).quantize(Decimal('1'), rounding=ROUND_DOWN))


def coins_for_recharge_amount(amount_yuan):
    amount = Decimal(str(amount_yuan or '0'))
    if amount <= 0:
        return 0
    ratio = _decimal_config('COINS_PER_YUAN', '10')
    return int((amount * ratio).quantize(Decimal('1'), rounding=ROUND_DOWN))


def estimate_tokens_from_text(text):
    content = (text or '').strip()
    if not content:
        return 0
    return max(1, (len(content) + 3) // 4)


def get_or_create_wallet(user_id, *, lock=False):
    wallet = WalletAccount.query.filter_by(user_id=user_id).first()
    if wallet is None:
        wallet = WalletAccount(user_id=user_id)
        db.session.add(wallet)
        db.session.flush()
    if lock:
        wallet = WalletAccount.query.filter_by(id=wallet.id).with_for_update().one()
    return wallet


def create_wallet_ledger(wallet, *, change_type, available_delta=0, reserved_delta=0, related_order_no=None, related_usage_id=None, idempotency_key=None, remark=None):
    ledger = WalletLedger(
        user_id=wallet.user_id,
        wallet_account_id=wallet.id,
        related_usage_id=related_usage_id,
        change_type=change_type,
        available_delta=int(available_delta or 0),
        reserved_delta=int(reserved_delta or 0),
        available_after=wallet.available_coins,
        reserved_after=wallet.reserved_coins,
        related_order_no=related_order_no,
        idempotency_key=idempotency_key,
        remark=remark,
    )
    db.session.add(ledger)
    return ledger


def create_recharge_order(user_id, *, amount_yuan, subject, order_no=None):
    amount = Decimal(str(amount_yuan or '0')).quantize(Decimal('0.01'))
    coins = coins_for_recharge_amount(amount)
    order = RechargeOrder(
        user_id=user_id,
        order_no=order_no or make_order_no(),
        amount_yuan=amount,
        coins=coins,
        subject=subject,
        status='pending',
        channel='alipay',
    )
    db.session.add(order)
    db.session.flush()
    return order


def apply_recharge(order, *, alipay_trade_no=None, buyer_logon_id=None, notify_payload=None):
    if order.status == 'paid':
        return order

    wallet = get_or_create_wallet(order.user_id, lock=True)
    wallet.available_coins += order.coins
    wallet.total_recharged_coins += order.coins
    order.status = 'paid'
    order.alipay_trade_no = alipay_trade_no or order.alipay_trade_no
    order.buyer_logon_id = buyer_logon_id or order.buyer_logon_id
    order.notify_payload = notify_payload or order.notify_payload
    order.paid_at = db.func.now()
    create_wallet_ledger(
        wallet,
        change_type='recharge',
        available_delta=order.coins,
        related_order_no=order.order_no,
        idempotency_key=f'recharge:{order.order_no}',
        remark=f'支付宝充值到账 {order.coins} 代币'
    )
    db.session.flush()
    return order


def reserve_usage_charge(user_id, *, request_id, endpoint, provider, model, estimated_tokens, call_id=None, remark=None):
    coins_reserved = coins_for_tokens(estimated_tokens)
    wallet = get_or_create_wallet(user_id, lock=True)
    if wallet.available_coins < coins_reserved:
        raise InsufficientBalanceError('余额不足，无法继续调用模型')

    wallet.available_coins -= coins_reserved
    wallet.reserved_coins += coins_reserved

    usage = LLMUsageRecord(
        user_id=user_id,
        request_id=request_id,
        call_id=call_id or make_call_id(),
        endpoint=endpoint,
        provider=provider,
        model=model,
        estimated_tokens=int(estimated_tokens or 0),
        coins_reserved=coins_reserved,
        status='reserved',
    )
    db.session.add(usage)
    db.session.flush()

    create_wallet_ledger(
        wallet,
        change_type='reserve',
        available_delta=-coins_reserved,
        reserved_delta=coins_reserved,
        related_usage_id=usage.id,
        idempotency_key=f'reserve:{usage.call_id}',
        remark=remark or f'{endpoint} 调用预占 {coins_reserved} 代币'
    )
    db.session.flush()
    return usage


def finalize_usage_charge(usage_id, *, prompt_tokens=0, completion_tokens=0, total_tokens=None, usage_source='provider'):
    usage = LLMUsageRecord.query.filter_by(id=usage_id).with_for_update().one()
    if usage.status == 'completed':
        return usage

    total = int(total_tokens if total_tokens is not None else (prompt_tokens or 0) + (completion_tokens or 0))
    actual_coins = coins_for_tokens(total)
    wallet = get_or_create_wallet(usage.user_id, lock=True)

    extra_needed = max(actual_coins - usage.coins_reserved, 0)
    if extra_needed and wallet.available_coins < extra_needed:
        raise InsufficientBalanceError('预占代币不足，且账户可用余额不足补扣')

    wallet.available_coins -= extra_needed
    wallet.reserved_coins -= usage.coins_reserved
    wallet.total_consumed_coins += actual_coins

    usage.prompt_tokens = int(prompt_tokens or 0)
    usage.completion_tokens = int(completion_tokens or 0)
    usage.total_tokens = total
    usage.coins_charged = actual_coins
    usage.usage_source = usage_source
    usage.status = 'completed'
    usage.finished_at = db.func.now()

    create_wallet_ledger(
        wallet,
        change_type='consume',
        available_delta=-extra_needed,
        reserved_delta=-usage.coins_reserved,
        related_usage_id=usage.id,
        idempotency_key=f'consume:{usage.call_id}',
        remark=f'{usage.endpoint} 实际消耗 {total} tokens，扣除 {actual_coins} 代币'
    )

    release_coins = max(usage.coins_reserved - actual_coins, 0)
    if release_coins:
        wallet.available_coins += release_coins
        create_wallet_ledger(
            wallet,
            change_type='release',
            available_delta=release_coins,
            related_usage_id=usage.id,
            idempotency_key=f'release:{usage.call_id}',
            remark=f'{usage.endpoint} 释放未用预占 {release_coins} 代币'
        )

    db.session.flush()
    return usage


def release_usage_reservation(usage_id, *, reason='调用失败，释放预占代币'):
    usage = LLMUsageRecord.query.filter_by(id=usage_id).with_for_update().one()
    if usage.status in ('released', 'failed'):
        return usage

    wallet = get_or_create_wallet(usage.user_id, lock=True)
    wallet.available_coins += usage.coins_reserved
    wallet.reserved_coins -= usage.coins_reserved
    usage.status = 'released'
    usage.error_message = reason
    usage.finished_at = db.func.now()

    create_wallet_ledger(
        wallet,
        change_type='release',
        available_delta=usage.coins_reserved,
        reserved_delta=-usage.coins_reserved,
        related_usage_id=usage.id,
        idempotency_key=f'usage-release:{usage.call_id}',
        remark=reason
    )
    db.session.flush()
    return usage