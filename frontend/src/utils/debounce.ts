/**
 * 创建一个防抖函数：在连续调用时只执行最后一次，延迟 delay 毫秒。
 * 同时内置节流：相邻两次执行至少间隔 delay 毫秒。
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number = 500,
): { (...args: Parameters<T>): void; cancel: () => void } {
  let timer: ReturnType<typeof setTimeout> | null = null
  let lastRun = 0

  const debounced = (...args: Parameters<T>) => {
    if (timer) clearTimeout(timer)
    const now = Date.now()
    const remaining = delay - (now - lastRun)
    if (remaining <= 0) {
      // 距上次执行已超过 delay，立即执行（节流）
      lastRun = now
      fn(...args)
    } else {
      // 否则等剩余时间后再执行
      timer = setTimeout(() => {
        lastRun = Date.now()
        timer = null
        fn(...args)
      }, remaining)
    }
  }

  debounced.cancel = () => {
    if (timer) { clearTimeout(timer); timer = null }
  }

  return debounced
}
