#!/usr/bin/env python3
# run_transformation_job.py
import argparse
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.job_executor import TransformationJobExecutor


def main():
    parser = argparse.ArgumentParser(description='Run a transformation job')
    parser.add_argument('--journey-id', required=True, help='Journey ID')
    parser.add_argument('--stage-id', required=True, help='Stage ID to execute')
    parser.add_argument('--triggered-by', default='system', help='Who triggered the job')
    parser.add_argument('--reason', default='Automated execution', help='Reason for execution')

    args = parser.parse_args()

    executor = TransformationJobExecutor()

    try:
        print(f'🚀 Starting job for journey: {args.journey_id}, stage: {args.stage_id}')

        # Start job execution
        job_id = executor.start_job_execution(
            journey_id=args.journey_id,
            stage_id=args.stage_id,
            triggered_by=args.triggered_by,
            reason=args.reason,
        )

        print(f'✅ Job started: {job_id}')

        # Execute the job
        executor.execute_job(args.journey_id, job_id)

        print(f'🎉 Job {job_id} completed successfully!')

    except Exception as e:
        print(f'❌ Job execution failed: {str(e)}')
        sys.exit(1)


if __name__ == '__main__':
    main()
