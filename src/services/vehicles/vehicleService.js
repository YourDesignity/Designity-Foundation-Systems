import BaseService from '../base/BaseService';

/**
 * Vehicle service.
 */
class VehicleService extends BaseService {
  constructor() {
    super('/vehicles');
  }

  /**
   * Get all vehicles.
   * @returns {Promise<Array>}
   */
  async getAll() {
    return this.get('/');
  }

  /**
   * Get vehicle by ID.
   * @param {number|string} id
   * @returns {Promise<Object>}
   */
  async getById(id) {
    return this.get(`/${id}`);
  }

  /**
   * Register a new vehicle.
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  async create(data) {
    return this.post('/', data);
  }

  /**
   * Get all vehicle trips.
   * @returns {Promise<Array>}
   */
  async getTrips() {
    return this.get('/trips');
  }

  /**
   * Start a new trip.
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  async startTrip(data) {
    return this.post('/trip/start', data);
  }

  /**
   * End an ongoing trip.
   * @param {number|string} tripId
   * @param {number} endMileage
   * @param {string} endCondition
   * @returns {Promise<Object>}
   */
  async endTrip(tripId, endMileage, endCondition) {
    return this.post(`/trip/end/${tripId}?end_mileage=${endMileage}&end_condition=${endCondition}`);
  }

  /**
   * Get all maintenance records.
   * @returns {Promise<Array>}
   */
  async getMaintenance() {
    return this.get('/maintenance');
  }

  /**
   * Add a maintenance record.
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  async addMaintenance(data) {
    return this.post('/maintenance', data);
  }

  /**
   * Get all fuel records.
   * @returns {Promise<Array>}
   */
  async getFuelRecords() {
    return this.get('/fuel');
  }

  /**
   * Add a fuel log entry.
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  async addFuelLog(data) {
    return this.post('/fuel', data);
  }

  /**
   * Get all vehicle expenses.
   * @returns {Promise<Array>}
   */
  async getExpenses() {
    return this.get('/expenses');
  }

  /**
   * Add a vehicle expense.
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  async addExpense(data) {
    return this.post('/expense', data);
  }
}

export default new VehicleService();
