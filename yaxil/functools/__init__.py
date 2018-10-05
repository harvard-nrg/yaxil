import pickle
from functools import wraps

def lru_cache(fn):
    '''
    Memoization wrapper that can handle function attributes, mutable arguments, 
    and can be applied either as a decorator or at runtime.

    :param fn: Function
    :type fn: function
    :returns: Memoized function
    :rtype: function
    '''
    @wraps(fn)
    def memoized_fn(*args):
        pargs = pickle.dumps(args)
        if pargs not in memoized_fn.cache:
            memoized_fn.cache[pargs] = fn(*args)
        return memoized_fn.cache[pargs]
    # propagate function attributes in the event that
    # this is applied as a function and not a decorator
    for attr, value in iter(fn.__dict__.items()):
        setattr(memoized_fn, attr, value)
    memoized_fn.cache = {}
    return memoized_fn

