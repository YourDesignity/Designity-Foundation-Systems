import BaseService from '../base/BaseService';

class FinanceService extends BaseService {
  constructor() {
    super('/finance');
  }

  async getSummary() {
    return this.get('/summary');
  }

  async getAdvancedSummary(qs = '') {
    return this.get(`/advanced-summary${qs}`);
  }
}

export default new FinanceService();
