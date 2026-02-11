"""
Fibonacci sequence calculator with various implementations.
"""


def fibonacci_recursive(n: int) -> int:
    """
    Calculate nth Fibonacci number using recursion.
    
    Args:
        n: The position in the Fibonacci sequence
        
    Returns:
        The nth Fibonacci number
        
    Note:
        This is inefficient for large n due to repeated calculations.
    """
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)


def fibonacci_iterative(n: int) -> int:
    """
    Calculate nth Fibonacci number using iteration.
    
    Args:
        n: The position in the Fibonacci sequence
        
    Returns:
        The nth Fibonacci number
        
    This is more efficient than the recursive version.
    """
    if n <= 1:
        return n
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def fibonacci_memoized(n: int, memo: dict = None) -> int:
    """
    Calculate nth Fibonacci number using memoization.
    
    Args:
        n: The position in the Fibonacci sequence
        memo: Optional dictionary to store computed values
        
    Returns:
        The nth Fibonacci number
        
    This combines recursion with caching for efficiency.
    """
    if memo is None:
        memo = {}
    
    if n in memo:
        return memo[n]
    
    if n <= 1:
        return n
    
    memo[n] = fibonacci_memoized(n - 1, memo) + fibonacci_memoized(n - 2, memo)
    return memo[n]


# Example usage
if __name__ == "__main__":
    n = 10
    print(f"Fibonacci({n}) = {fibonacci_iterative(n)}")
