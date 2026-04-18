import { useState, useEffect } from 'react';

/**
 * Debounce a value by the given delay (default 300ms).
 * @param {*} value
 * @param {number} delay
 * @returns {*} debounced value
 */
const useDebounce = (value, delay = 300) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

export default useDebounce;
