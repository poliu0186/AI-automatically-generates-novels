import argparse
import multiprocessing
import signal
import time

from waitress import serve

from app import create_app


def serve_one(host, port, threads):
    app = create_app()
    serve(app, host=host, port=port, threads=threads)


def build_parser():
    parser = argparse.ArgumentParser(description='Run multiple app instances on sequential ports.')
    parser.add_argument('--host', default='0.0.0.0', help='Bind host for all instances')
    parser.add_argument('--start-port', type=int, default=60001, help='First instance port')
    parser.add_argument('--instances', type=int, default=2, help='Number of instances to run')
    parser.add_argument('--threads', type=int, default=8, help='Threads per instance (waitress)')
    return parser


def main():
    args = build_parser().parse_args()

    if args.instances < 1:
        raise ValueError('--instances must be >= 1')
    if args.threads < 1:
        raise ValueError('--threads must be >= 1')

    procs = []
    for i in range(args.instances):
        port = args.start_port + i
        proc = multiprocessing.Process(target=serve_one, args=(args.host, port, args.threads), daemon=False)
        proc.start()
        procs.append((proc, port))
        print(f'[multi-instance] started pid={proc.pid} host={args.host} port={port} threads={args.threads}', flush=True)

    def shutdown(signum=None, frame=None):
        print('[multi-instance] stopping instances...', flush=True)
        for proc, _ in procs:
            if proc.is_alive():
                proc.terminate()
        for proc, _ in procs:
            proc.join(timeout=5)
        print('[multi-instance] all instances stopped', flush=True)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            alive = [proc for proc, _ in procs if proc.is_alive()]
            if len(alive) != len(procs):
                print('[multi-instance] detected instance exit, shutting down all...', flush=True)
                shutdown()
                break
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()


if __name__ == '__main__':
    main()
