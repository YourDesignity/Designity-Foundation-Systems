import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Card, Avatar, Button, Input, Tag, Typography, Space,
  message, theme, Row, Col, Spin, Badge, Empty, Modal, Select
} from 'antd';
import {
  SendOutlined, UserOutlined, GlobalOutlined, MessageFilled,
  TeamOutlined, ReloadOutlined, CommentOutlined
} from '@ant-design/icons';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

const { Title, Text } = Typography;
const { TextArea } = Input;
const { useToken } = theme;

const API_BASE_URL = 'http://localhost:8000';

const ManagerMessagesPage = () => {
  const { user } = useAuth();
  const { token } = useToken();

  const [loading, setLoading] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [replyText, setReplyText] = useState('');
  const [sendingReply, setSendingReply] = useState(false);

  // New Message Modal state
  const [isNewMessageModalOpen, setIsNewMessageModalOpen] = useState(false);
  const [recipients, setRecipients] = useState({ admins: [], employees: [] });
  const [selectedRecipientId, setSelectedRecipientId] = useState(null);
  const [newMessageText, setNewMessageText] = useState('');
  const [sendingNewMessage, setSendingNewMessage] = useState(false);

  const selectedConversationRef = useRef(null);

  // =============================================================================
  // API HELPERS
  // =============================================================================

  const getAuthHeaders = () => {
    const accessToken = localStorage.getItem('access_token');
    return { headers: { Authorization: `Bearer ${accessToken}` } };
  };

  // =============================================================================
  // LOAD DATA
  // =============================================================================

  const loadConversations = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API_BASE_URL}/messages/conversations`, getAuthHeaders());
      setConversations(res.data);
    } catch (err) {
      message.error('Failed to load conversations');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadMessages = async (conversationId) => {
    try {
      const res = await axios.get(
        `${API_BASE_URL}/messages/${conversationId}/messages`,
        getAuthHeaders()
      );
      setMessages(res.data);

      setTimeout(() => {
        const container = document.getElementById('manager-messages-container');
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      }, 100);
    } catch (err) {
      message.error('Failed to load messages');
      console.error(err);
    }
  };

  const loadRecipients = async () => {
    try {
      const res = await axios.get(
        `${API_BASE_URL}/messages/manager-recipients`,
        getAuthHeaders()
      );
      setRecipients(res.data);
    } catch (err) {
      message.error('Failed to load recipients');
      console.error(err);
    }
  };

  // Initial load + polling every 5 seconds
  useEffect(() => {
    loadConversations();
    loadRecipients();

    const interval = setInterval(() => {
      loadConversations();
      if (selectedConversationRef.current) {
        loadMessages(selectedConversationRef.current.id);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // Keep ref in sync; load messages when conversation changes
  useEffect(() => {
    selectedConversationRef.current = selectedConversation;
    if (selectedConversation) {
      loadMessages(selectedConversation.id);
    }
  }, [selectedConversation]);

  // =============================================================================
  // SEND REPLY
  // =============================================================================

  const handleReply = async () => {
    if (!replyText.trim() || !selectedConversation) {
      message.warning('Please type a message');
      return;
    }

    try {
      setSendingReply(true);
      await axios.post(
        `${API_BASE_URL}/messages/${selectedConversation.id}/reply`,
        null,
        {
          ...getAuthHeaders(),
          params: { content: replyText },
        }
      );

      message.success('Reply sent!');
      setReplyText('');
      await loadMessages(selectedConversation.id);
      await loadConversations();
    } catch (err) {
      message.error(err.response?.data?.detail || 'Failed to send reply');
      console.error(err);
    } finally {
      setSendingReply(false);
    }
  };

  const handleSendNewMessage = async () => {
    if (!newMessageText.trim() || !selectedRecipientId) {
      message.warning('Please select a recipient and type a message');
      return;
    }

    try {
      setSendingNewMessage(true);
      await axios.post(
        `${API_BASE_URL}/messages/private/${selectedRecipientId}`,
        null,
        {
          ...getAuthHeaders(),
          params: { content: newMessageText },
        }
      );

      message.success('Message sent successfully!');
      setNewMessageText('');
      setSelectedRecipientId(null);
      setIsNewMessageModalOpen(false);
      await loadConversations();
    } catch (err) {
      message.error(err.response?.data?.detail || 'Failed to send message');
      console.error(err);
    } finally {
      setSendingNewMessage(false);
    }
  };

  // =============================================================================
  // UI HELPERS
  // =============================================================================

  const getConversationIcon = (type) => {
    switch (type) {
      case 'broadcast_all':
        return <GlobalOutlined style={{ color: '#1890ff' }} />;
      case 'broadcast_managers':
        return <TeamOutlined style={{ color: '#52c41a' }} />;
      case 'broadcast_employees':
        return <UserOutlined style={{ color: '#fa8c16' }} />;
      case 'broadcast_custom':
        return <MessageFilled style={{ color: '#722ed1' }} />;
      case 'private':
        return <CommentOutlined style={{ color: '#eb2f96' }} />;
      default:
        return <MessageFilled />;
    }
  };

  const totalUnread = useMemo(() => {
    return conversations.reduce((sum, conv) => sum + conv.unread_count, 0);
  }, [conversations]);

  const formatTimestamp = (timestamp) => dayjs(timestamp).fromNow();

  // =============================================================================
  // RENDER
  // =============================================================================

  return (
    <div
      style={{
        padding: '24px',
        maxWidth: '1400px',
        margin: '0 auto',
        height: 'calc(100vh - 100px)',
      }}
    >
      {/* HEADER */}
      <Card variant="borderless" style={{ marginBottom: 24 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Title level={3} style={{ margin: 0 }}>
              <MessageFilled style={{ marginRight: 8, color: '#1890ff' }} />
              My Messages
              {totalUnread > 0 && (
                <Badge
                  count={totalUnread}
                  style={{ marginLeft: 12 }}
                  overflowCount={99}
                />
              )}
            </Title>
            <Text type="secondary">Your inbox – read and reply to messages</Text>
          </Col>
          <Col>
            <Space>
              <Button
                type="primary"
                icon={<CommentOutlined />}
                onClick={() => setIsNewMessageModalOpen(true)}
              >
                New Message
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => {
                  loadConversations();
                  if (selectedConversation) loadMessages(selectedConversation.id);
                }}
                loading={loading}
              >
                Refresh
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* MAIN CONTENT */}
      <Row gutter={24} style={{ height: 'calc(100% - 120px)' }}>
        {/* LEFT: CONVERSATION LIST */}
        <Col xs={24} md={8} style={{ height: '100%' }}>
          <Card
            title={
              <Space>
                <span>Conversations</span>
                <Badge
                  count={conversations.length}
                  style={{ backgroundColor: '#1890ff' }}
                  overflowCount={999}
                />
              </Space>
            }
            variant="borderless"
            styles={{
              body: {
                height: 'calc(100% - 60px)',
                overflowY: 'auto',
                padding: 12,
              }
            }}
            style={{ height: '100%' }}
          >
            {loading && conversations.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin size="large">
                  <div style={{ padding: 50 }} />
                </Spin>
                <div style={{ marginTop: 16, color: '#999' }}>Loading conversations...</div>
              </div>
            )}

            {!loading && conversations.length === 0 && (
              <Empty
                description="No conversations yet"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}

            <div>
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  onClick={() => setSelectedConversation(conv)}
                  style={{
                    cursor: 'pointer',
                    borderRadius: 8,
                    padding: '10px 12px',
                    marginBottom: 4,
                    backgroundColor:
                      selectedConversation?.id === conv.id
                        ? token.colorPrimaryBg
                        : conv.unread_count > 0
                        ? '#fff7e6'
                        : '#fff',
                    border:
                      selectedConversation?.id === conv.id
                        ? `1px solid ${token.colorPrimary}`
                        : '1px solid #f0f0f0',
                    transition: 'all 0.15s',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                  }}
                >
                  <Badge count={conv.unread_count} size="small">
                    <Avatar
                      icon={getConversationIcon(conv.conversation_type)}
                      style={{ backgroundColor: token.colorPrimaryBg }}
                    />
                  </Badge>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Text
                      strong={conv.unread_count > 0}
                      style={{ fontSize: 13, display: 'block' }}
                      ellipsis
                    >
                      {conv.title || 'Conversation'}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12, display: 'block' }} ellipsis>
                      {conv.last_message || 'No messages yet'}
                    </Text>
                  </div>

                  <div style={{ fontSize: 11, color: '#aaa', whiteSpace: 'nowrap' }}>
                    {conv.last_activity ? formatTimestamp(conv.last_activity) : ''}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        {/* RIGHT: MESSAGE THREAD */}
        <Col xs={24} md={16} style={{ height: '100%' }}>
          <Card
            variant="borderless"
            styles={{
              body: { padding: 0, height: '100%', display: 'flex', flexDirection: 'column' }
            }}
            style={{ height: '100%' }}
          >
            {/* No conversation selected */}
            {!selectedConversation && (
              <div
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: '#fafafa',
                }}
              >
                <Empty
                  description="Select a conversation to view messages"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              </div>
            )}

            {selectedConversation && (
              <>
                {/* Conversation header */}
                <div
                  style={{
                    padding: '16px 24px',
                    borderBottom: '1px solid #f0f0f0',
                    backgroundColor: '#fff',
                  }}
                >
                  <Space>
                    <Avatar
                      icon={getConversationIcon(selectedConversation.conversation_type)}
                      style={{ backgroundColor: token.colorPrimaryBg }}
                    />
                    <div>
                      <Text strong>
                        {selectedConversation.title || 'Conversation'}
                      </Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {selectedConversation.participant_count || 0} participants
                      </Text>
                    </div>
                  </Space>
                </div>

                {/* Messages */}
                <div
                  id="manager-messages-container"
                  style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '16px 24px',
                    backgroundColor: '#fafafa',
                  }}
                >
                  {messages.length === 0 && (
                    <div style={{ textAlign: 'center', padding: 40 }}>
                      <Empty
                        description="No messages yet"
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                      />
                    </div>
                  )}

                  {messages.map((msg) => {
                    const isMyMessage = msg.sender_id === user?.uid;
                    return (
                      <div
                        key={msg.id}
                        style={{
                          display: 'flex',
                          justifyContent: isMyMessage ? 'flex-end' : 'flex-start',
                          marginBottom: 16,
                        }}
                      >
                        <div
                          style={{
                            maxWidth: '70%',
                            display: 'flex',
                            flexDirection: isMyMessage ? 'row-reverse' : 'row',
                            gap: 8,
                            alignItems: 'flex-start',
                          }}
                        >
                          <Avatar
                            icon={<UserOutlined />}
                            size={32}
                            style={{
                              backgroundColor: isMyMessage
                                ? token.colorPrimary
                                : '#d9d9d9',
                              flexShrink: 0,
                            }}
                          />
                          <div>
                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 6,
                                marginBottom: 4,
                                flexDirection: isMyMessage ? 'row-reverse' : 'row',
                              }}
                            >
                              <Text strong style={{ fontSize: 12 }}>
                                {msg.sender_name}
                              </Text>
                              <Tag
                                color={isMyMessage ? 'blue' : 'default'}
                                style={{ fontSize: 10, lineHeight: '16px' }}
                              >
                                {msg.sender_role}
                              </Tag>
                              <Text type="secondary" style={{ fontSize: 11 }}>
                                {formatTimestamp(msg.timestamp)}
                              </Text>
                            </div>
                            <div
                              style={{
                                backgroundColor: isMyMessage
                                  ? token.colorPrimary
                                  : '#fff',
                                color: isMyMessage ? '#fff' : '#000',
                                padding: '10px 14px',
                                borderRadius: isMyMessage
                                  ? '16px 4px 16px 16px'
                                  : '4px 16px 16px 16px',
                                boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                                wordBreak: 'break-word',
                              }}
                            >
                              {msg.content}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Reply box */}
                <div
                  style={{
                    padding: '16px 24px',
                    borderTop: '1px solid #f0f0f0',
                    backgroundColor: '#fff',
                  }}
                >
                  <Space.Compact style={{ width: '100%' }}>
                    <TextArea
                      value={replyText}
                      onChange={(e) => setReplyText(e.target.value)}
                      placeholder="Type a reply..."
                      autoSize={{ minRows: 1, maxRows: 4 }}
                      onPressEnter={(e) => {
                        if (!e.shiftKey) {
                          e.preventDefault();
                          handleReply();
                        }
                      }}
                      style={{ borderRadius: '8px 0 0 8px' }}
                    />
                    <Button
                      type="primary"
                      icon={<SendOutlined />}
                      onClick={handleReply}
                      loading={sendingReply}
                      style={{ height: 'auto', borderRadius: '0 8px 8px 0' }}
                    >
                      Send
                    </Button>
                  </Space.Compact>
                  <Text type="secondary" style={{ fontSize: 11, marginTop: 4, display: 'block' }}>
                    Press Enter to send, Shift+Enter for new line
                  </Text>
                </div>
              </>
            )}
          </Card>
        </Col>
      </Row>

      {/* NEW MESSAGE MODAL */}
      <Modal
        title="📨 Send New Message"
        open={isNewMessageModalOpen}
        onCancel={() => {
          setIsNewMessageModalOpen(false);
          setNewMessageText('');
          setSelectedRecipientId(null);
        }}
        footer={null}
        width={600}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Text strong>Send Message To:</Text>
            <Select
              placeholder="Select a person..."
              value={selectedRecipientId}
              onChange={setSelectedRecipientId}
              style={{ width: '100%', marginTop: 8 }}
              size="large"
              showSearch
              filterOption={(input, option) =>
                String(option.children || '').toLowerCase().includes(input.toLowerCase())
              }
            >
              {recipients.admins && recipients.admins.length > 0 && (
                <Select.OptGroup label="👔 Admins">
                  {recipients.admins.map(admin => (
                    <Select.Option key={admin.id} value={admin.id}>
                      {admin.name} ({admin.role})
                    </Select.Option>
                  ))}
                </Select.OptGroup>
              )}

              {recipients.employees && recipients.employees.length > 0 && (
                <Select.OptGroup label="👷 My Employees">
                  {recipients.employees.map(emp => (
                    <Select.Option key={emp.id} value={emp.id}>
                      {emp.name} - {emp.designation}
                    </Select.Option>
                  ))}
                </Select.OptGroup>
              )}
            </Select>
          </div>

          <div>
            <Text strong>Message:</Text>
            <TextArea
              value={newMessageText}
              onChange={(e) => setNewMessageText(e.target.value)}
              placeholder="Type your message here..."
              autoSize={{ minRows: 4, maxRows: 8 }}
              style={{ marginTop: 8 }}
            />
          </div>

          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSendNewMessage}
            loading={sendingNewMessage}
            block
            size="large"
          >
            Send Message
          </Button>
        </Space>
      </Modal>
    </div>
  );
};

export default ManagerMessagesPage;
