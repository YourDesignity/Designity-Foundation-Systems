import React, { useState, useEffect } from 'react';
import { Modal, Select, message, Spin } from 'antd';
import { fetchWithAuth } from '../../services/apiService';

const AssignManagerModal = ({ visible, site, onCancel, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [managers, setManagers] = useState([]);
  const [fetchingManagers, setFetchingManagers] = useState(false);
  const [selectedManagerId, setSelectedManagerId] = useState(null);

  useEffect(() => {
    if (visible) {
      fetchManagers();
      setSelectedManagerId(site?.assigned_manager_id || null);
    }
  }, [visible, site]);

  const fetchManagers = async () => {
    setFetchingManagers(true);
    try {
      const data = await fetchWithAuth('/workflow/sites/managers');
      setManagers(Array.isArray(data) ? data : []);
    } catch (error) {
      // Fallback: try managers endpoint
      try {
        const data = await fetchWithAuth('/admins/managers');
        setManagers(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Error fetching managers:', err);
        message.error('Could not load managers');
      }
    } finally {
      setFetchingManagers(false);
    }
  };

  const handleAssign = async () => {
    if (!selectedManagerId) {
      message.warning('Please select a manager');
      return;
    }

    setLoading(true);
    try {
      const data = await fetchWithAuth(`/workflow/sites/${site.uid}/assign-manager`, {
        method: 'POST',
        body: JSON.stringify({ manager_id: selectedManagerId }),
      });
      message.success(data.message || 'Manager assigned successfully');
      onSuccess(data);
    } catch (error) {
      console.error('Error assigning manager:', error);
      message.error(error.message || 'Error assigning manager');
    } finally {
      setLoading(false);
    }
  };

  const handleUnassign = async () => {
    setLoading(true);
    try {
      await fetchWithAuth(`/workflow/sites/${site.uid}/unassign-manager`, {
        method: 'DELETE',
      });
      message.success('Manager unassigned successfully');
      onSuccess({ manager_id: null, manager_name: null });
    } catch (error) {
      console.error('Error unassigning manager:', error);
      message.error(error.message || 'Error unassigning manager');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={`Assign Manager – ${site?.site_code || ''}`}
      open={visible}
      onOk={handleAssign}
      onCancel={onCancel}
      okText="Assign Manager"
      confirmLoading={loading}
      okButtonProps={{ disabled: !selectedManagerId }}
      extra={
        site?.assigned_manager_id && (
          <a onClick={handleUnassign} style={{ color: 'red' }}>
            Unassign Current Manager
          </a>
        )
      }
    >
      {site?.assigned_manager_name && (
        <p style={{ marginBottom: 12, color: '#666' }}>
          Current manager: <strong>{site.assigned_manager_name}</strong>
        </p>
      )}

      {fetchingManagers ? (
        <Spin />
      ) : (
        <Select
          showSearch
          style={{ width: '100%' }}
          placeholder="Select a Site Manager"
          value={selectedManagerId}
          onChange={setSelectedManagerId}
          optionFilterProp="children"
          filterOption={(input, option) =>
            (option?.children ?? '').toLowerCase().includes(input.toLowerCase())
          }
        >
          {managers.map((m) => (
            <Select.Option key={m.uid ?? m.id} value={m.uid ?? m.id}>
              {m.full_name || m.name} – {m.email || ''}
            </Select.Option>
          ))}
        </Select>
      )}

      {site?.assigned_manager_id && (
        <div style={{ marginTop: 12 }}>
          <a
            onClick={handleUnassign}
            style={{ color: '#ff4d4f', cursor: 'pointer' }}
          >
            Remove current manager assignment
          </a>
        </div>
      )}
    </Modal>
  );
};

export default AssignManagerModal;
