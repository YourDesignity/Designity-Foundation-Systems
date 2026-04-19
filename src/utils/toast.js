import { toast as reactToast } from 'react-toastify';

export const toast = {
  success: (message) => reactToast.success(message),
  error: (message) => reactToast.error(message),
  info: (message) => reactToast.info(message),
  warning: (message) => reactToast.warning(message),
  promise: (promise, messages) => reactToast.promise(promise, messages),
};
