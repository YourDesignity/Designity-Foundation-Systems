import BaseService from '../base/BaseService';

/**
 * Messaging service.
 */
class MessagingService extends BaseService {
  constructor() {
    super('/messages');
  }

  /**
   * Get conversations.
   * @returns {Promise<Array>}
   */
  async getConversations() {
    // TODO: Implement in Phase 4B
    return this.get('/conversations');
  }

  /**
   * Send message.
   * @param {Object} payload
   * @returns {Promise<Object>}
   */
  async send(payload) {
    // TODO: Implement in Phase 4B
    return this.post('/send', payload);
  }
}

export default new MessagingService();
