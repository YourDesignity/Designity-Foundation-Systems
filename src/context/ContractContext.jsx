/**
 * ContractContext.jsx
 *
 * React Context for the Modular Contract Workflow System (Phase 6).
 * Provides contract state, active contract tracking, and helper actions
 * to all child components without prop-drilling.
 */

import React, { createContext, useContext, useReducer, useCallback } from 'react';

// ─── Initial state ────────────────────────────────────────────────────────────

const initialState = {
  /** Currently open/selected contract */
  activeContract: null,
  /** Cached list of contracts (set by ContractListPage) */
  contractList: [],
  /** Pending approval count for badge display */
  pendingApprovalCount: 0,
  /** Whether any contract data is loading */
  isLoading: false,
  /** Last error message */
  error: null,
};

// ─── Reducer ──────────────────────────────────────────────────────────────────

const contractReducer = (state, action) => {
  switch (action.type) {
    case 'SET_ACTIVE_CONTRACT':
      return { ...state, activeContract: action.payload };

    case 'UPDATE_ACTIVE_CONTRACT':
      return {
        ...state,
        activeContract: state.activeContract
          ? { ...state.activeContract, ...action.payload }
          : action.payload,
      };

    case 'CLEAR_ACTIVE_CONTRACT':
      return { ...state, activeContract: null };

    case 'SET_CONTRACT_LIST':
      return { ...state, contractList: action.payload };

    case 'UPDATE_CONTRACT_IN_LIST': {
      const updated = state.contractList.map((c) =>
        c.uid === action.payload.uid ? { ...c, ...action.payload } : c
      );
      return { ...state, contractList: updated };
    }

    case 'REMOVE_CONTRACT_FROM_LIST':
      return {
        ...state,
        contractList: state.contractList.filter((c) => c.uid !== action.payload),
      };

    case 'SET_PENDING_APPROVALS':
      return { ...state, pendingApprovalCount: action.payload };

    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };

    case 'SET_ERROR':
      return { ...state, error: action.payload };

    case 'CLEAR_ERROR':
      return { ...state, error: null };

    default:
      return state;
  }
};

// ─── Context ──────────────────────────────────────────────────────────────────

const ContractContext = createContext(null);

// ─── Provider ─────────────────────────────────────────────────────────────────

export const ContractProvider = ({ children }) => {
  const [state, dispatch] = useReducer(contractReducer, initialState);

  const setActiveContract = useCallback(
    (contract) => dispatch({ type: 'SET_ACTIVE_CONTRACT', payload: contract }),
    []
  );

  const updateActiveContract = useCallback(
    (updates) => dispatch({ type: 'UPDATE_ACTIVE_CONTRACT', payload: updates }),
    []
  );

  const clearActiveContract = useCallback(
    () => dispatch({ type: 'CLEAR_ACTIVE_CONTRACT' }),
    []
  );

  const setContractList = useCallback(
    (list) => dispatch({ type: 'SET_CONTRACT_LIST', payload: list }),
    []
  );

  const updateContractInList = useCallback(
    (contract) => dispatch({ type: 'UPDATE_CONTRACT_IN_LIST', payload: contract }),
    []
  );

  const removeContractFromList = useCallback(
    (uid) => dispatch({ type: 'REMOVE_CONTRACT_FROM_LIST', payload: uid }),
    []
  );

  const setPendingApprovalCount = useCallback(
    (count) => dispatch({ type: 'SET_PENDING_APPROVALS', payload: count }),
    []
  );

  const setLoading = useCallback(
    (loading) => dispatch({ type: 'SET_LOADING', payload: loading }),
    []
  );

  const setError = useCallback(
    (error) => dispatch({ type: 'SET_ERROR', payload: error }),
    []
  );

  const clearError = useCallback(
    () => dispatch({ type: 'CLEAR_ERROR' }),
    []
  );

  const value = {
    // State
    ...state,
    // Actions
    setActiveContract,
    updateActiveContract,
    clearActiveContract,
    setContractList,
    updateContractInList,
    removeContractFromList,
    setPendingApprovalCount,
    setLoading,
    setError,
    clearError,
  };

  return (
    <ContractContext.Provider value={value}>
      {children}
    </ContractContext.Provider>
  );
};

// ─── Hook ─────────────────────────────────────────────────────────────────────

export const useContract = () => {
  const context = useContext(ContractContext);
  if (!context) {
    throw new Error('useContract must be used within a ContractProvider');
  }
  return context;
};

export default ContractContext;
