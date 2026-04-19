import tempWorkerService from './assignments/tempWorkerService';

export const assignTempWorkers = (siteId, workers, replacementReason = null) =>
  tempWorkerService.assignTempWorkers(siteId, workers, replacementReason);

export const getAvailableTempWorkers = () => tempWorkerService.getAvailableTempWorkers();

export const registerTempWorker = (data) => tempWorkerService.registerTempWorker(data);

export const getTempWorkersAtSite = (siteId) => tempWorkerService.getTempWorkersAtSite(siteId);

export const endTempAssignment = (assignmentId) => tempWorkerService.endTempAssignment(assignmentId);

export const getCostSummary = (filters = {}) => tempWorkerService.getCostSummary(filters);

export const getAllTempWorkers = (availableOnly = null) =>
  tempWorkerService.getAllTempWorkers(availableOnly);

export const getWorkerHistory = (workerId) => tempWorkerService.getWorkerHistory(workerId);

export const getTempAssignments = (filters = {}) => tempWorkerService.getTempAssignments(filters);

export default {
  assignTempWorkers,
  getAvailableTempWorkers,
  registerTempWorker,
  getTempWorkersAtSite,
  endTempAssignment,
  getCostSummary,
  getAllTempWorkers,
  getWorkerHistory,
  getTempAssignments,
};
