import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { invoiceService } from '../services';

/**
 * Fetch all invoices.
 */
export const useInvoices = () => {
  return useQuery({
    queryKey: ['invoices'],
    queryFn: () => invoiceService.getAll(),
  });
};

/**
 * Create a new invoice.
 * @returns {UseMutationResult}
 */
export const useCreateInvoice = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => invoiceService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast.success('Invoice created successfully!');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to create invoice');
    },
  });
};

// TODO: Phase 4C - implement remaining invoice hooks (useInvoice, useUpdateInvoice, useDeleteInvoice, useInvoicePDF)
