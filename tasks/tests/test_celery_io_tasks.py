# !/usr/bin/env python
# -*-coding:utf-8 -*-
"""
File       : test_celery_io_tasks.py
Time       ：2025/7/31 10:25
Author     ：TyroneTian
Email      : zhichao.tian@medalsoft.com
Description：
"""
import time

from tasks.example.task import add


def test_concurrent_add_sync(num_tasks=100):
    """同步方式测试并发 - 使用线程池"""
    print(f"开始同步并发测试，任务数量: {num_tasks}")
    start_time = time.time()

    # 提交所有任务
    tasks = []
    for i in range(num_tasks):
        result = add.delay(i, i + 1)
        tasks.append(result)

    print(f"所有 {num_tasks} 个任务已提交，用时: {time.time() - start_time:.2f}秒")

    # 等待所有任务完成
    success_count = 0
    error_count = 0

    for i, task in enumerate(tasks):
        try:
            # 设置超时时间，避免无限等待
            result = task.get(timeout=30)
            success_count += 1
            print(f"任务 {i + 1} 完成: {result}")
        except Exception as e:
            error_count += 1
            print(f"任务 {i + 1} 失败: {e}")

    total_time = time.time() - start_time
    print("\n测试完成:")
    print(f"总用时: {total_time:.2f}秒")
    print(f"成功任务: {success_count}")
    print(f"失败任务: {error_count}")
    print(f"成功率: {success_count / num_tasks * 100:.2f}%")


def test_concurrent_add_with_monitoring(num_tasks=100):
    """带监控的并发测试"""
    print(f"开始带监控的并发测试，任务数量: {num_tasks}")
    start_time = time.time()

    # 提交所有任务
    tasks = []
    for i in range(num_tasks):
        result = add.delay(i, i + 1)
        tasks.append((i, result))

    print(f"所有 {num_tasks} 个任务已提交")

    # 监控任务状态
    completed = 0
    success_count = 0
    error_count = 0

    while completed < num_tasks:
        for i, (task_id, task) in enumerate(tasks):
            if task.ready() and task_id != -1:  # -1 表示已处理
                try:
                    result = task.get()
                    success_count += 1
                    print(f"✓ 任务 {task_id + 1} 完成: {result}")
                except Exception as e:
                    error_count += 1
                    print(f"✗ 任务 {task_id + 1} 失败: {e}")

                tasks[i] = (-1, task)  # 标记为已处理
                completed += 1

        # 避免过度轮询
        time.sleep(0.1)

        # 显示进度
        if completed % 10 == 0 or completed == num_tasks:
            elapsed = time.time() - start_time
            print(
                f"进度: {completed}/{num_tasks} ({completed / num_tasks * 100:.1f}%) - 用时: {elapsed:.2f}秒"
            )

    total_time = time.time() - start_time
    print(f"\n监控测试完成:")  # noqa
    print(f"总用时: {total_time:.2f}秒")  # noqa
    print(f"成功任务: {success_count}")  # noqa
    print(f"失败任务: {error_count}")  # noqa
    print(f"成功率: {success_count / num_tasks * 100:.2f}%")  # noqa


def test_batch_concurrent(batch_size=10, num_batches=10):
    """分批并发测试"""
    total_tasks = batch_size * num_batches
    print(f"开始分批并发测试: {num_batches} 批，每批 {batch_size} 个任务，总计 {total_tasks} 个")

    start_time = time.time()
    total_success = 0
    total_error = 0

    for batch_num in range(num_batches):
        print(f"\n执行第 {batch_num + 1} 批...")
        batch_start = time.time()

        # 提交当前批次的任务
        batch_tasks = []
        for i in range(batch_size):
            task_id = batch_num * batch_size + i
            result = add.delay(task_id, task_id + 1)
            batch_tasks.append(result)

        # 等待当前批次完成
        batch_success = 0
        batch_error = 0

        for task in batch_tasks:
            try:
                result = task.get(timeout=30)
                batch_success += 1
            except Exception as e:
                batch_error += 1
                print(f"批次 {batch_num + 1} 中的任务失败: {e}")

        batch_time = time.time() - batch_start
        total_success += batch_success
        total_error += batch_error

        print(
            f"第 {batch_num + 1} 批完成: 成功 {batch_success}/{batch_size}, 用时 {batch_time:.2f}秒"
        )

        # 批次间稍作休息
        if batch_num < num_batches - 1:
            time.sleep(1)

    total_time = time.time() - start_time
    print(f"\n分批测试完成:")  # noqa
    print(f"总用时: {total_time:.2f}秒")  # noqa
    print(f"成功任务: {total_success}/{total_tasks}")  # noqa
    print(f"失败任务: {total_error}/{total_tasks}")  # noqa
    print(f"成功率: {total_success / total_tasks * 100:.2f}%")  # noqa


def stress_test_with_stats(num_tasks=100, timeout=60):
    """压力测试并收集详细统计信息"""
    print(f"开始压力测试，任务数量: {num_tasks}，超时时间: {timeout}秒")

    start_time = time.time()
    submit_times = []
    completion_times = []

    # 提交所有任务并记录提交时间
    tasks = []
    for i in range(num_tasks):
        task_start = time.time()
        result = add.delay(i, i + 1)
        submit_time = time.time() - task_start
        submit_times.append(submit_time)
        tasks.append((result, time.time()))  # 保存任务和提交时间

    submit_end_time = time.time()
    print(f"所有任务提交完成，用时: {submit_end_time - start_time:.2f}秒")
    print(f"平均提交时间: {sum(submit_times) / len(submit_times) * 1000:.2f}ms")

    # 等待所有任务完成并收集统计
    success_count = 0
    error_count = 0

    for i, (task, submit_time) in enumerate(tasks):
        try:
            result = task.get(timeout=timeout)
            completion_time = time.time() - submit_time
            completion_times.append(completion_time)
            success_count += 1

            if i % 20 == 0:  # 每20个任务显示一次进度
                print(f"已完成 {i + 1} 个任务...")

        except Exception as e:
            error_count += 1
            print(f"任务 {i + 1} 失败: {e}")

    total_time = time.time() - start_time

    # 统计信息
    print(f"\n压力测试统计:")  # noqa
    print(f"总用时: {total_time:.2f}秒")
    print(f"成功任务: {success_count}/{num_tasks}")
    print(f"失败任务: {error_count}/{num_tasks}")
    print(f"成功率: {success_count / num_tasks * 100:.2f}%")

    if completion_times:
        print(f"任务完成时间统计:")  # noqa
        print(f"  最短: {min(completion_times):.2f}秒")  # noqa
        print(f"  最长: {max(completion_times):.2f}秒")  # noqa
        print(f"  平均: {sum(completion_times) / len(completion_times):.2f}秒")  # noqa
        print(f"  吞吐量: {success_count / total_time:.2f} 任务/秒")  # noqa


if __name__ == "__main__":
    print("Celery Eventlet 并发测试")
    print("=" * 50)

    # 选择测试类型
    # test_type = input("选择测试类型 (1:基础并发 2:监控测试 3:分批测试 4:压力测试): ").strip()
    for test_type in range(4):
        if test_type == 1:
            num_tasks = int(input("输入并发任务数量 (默认100): ") or "100")
            test_concurrent_add_sync(num_tasks)

        elif test_type == 2:
            num_tasks = int(input("输入并发任务数量 (默认100): ") or "100")
            test_concurrent_add_with_monitoring(num_tasks)

        elif test_type == 3:
            batch_size = int(input("输入每批任务数量 (默认10): ") or "10")
            num_batches = int(input("输入批次数量 (默认10): ") or "10")
            test_batch_concurrent(batch_size, num_batches)

        elif test_type == 4:
            num_tasks = int(input("输入任务数量 (默认100): ") or "100")
            timeout = int(input("输入超时时间/秒 (默认60): ") or "60")
            stress_test_with_stats(num_tasks, timeout)

        else:
            print("默认运行基础并发测试...")
            test_concurrent_add_sync(100)
