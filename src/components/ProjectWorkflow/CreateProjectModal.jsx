import React, { useState } from 'react';
import { Modal, Form, Input, Steps, Button } from 'antd';
import { ProjectOutlined, UserOutlined, FileTextOutlined } from '@ant-design/icons';
import { fetchWithAuth } from '../../services/apiService';
import { message } from 'antd';

const { TextArea } = Input;

const steps = [
  { title: 'Project Info', icon: <ProjectOutlined /> },
  { title: 'Client Info', icon: <UserOutlined /> },
  { title: 'Description', icon: <FileTextOutlined /> },
];

const fieldsByStep = {
  0: ['project_name'],
  1: ['client_name'],
  2: [],
};

const CreateProjectModal = ({ visible, onCancel, onSuccess }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  const handleNext = async () => {
    try {
      const fieldsToValidate = fieldsByStep[currentStep] || [];
      if (fieldsToValidate.length > 0) {
        await form.validateFields(fieldsToValidate);
      }
      if (currentStep < steps.length - 1) {
        setCurrentStep((s) => s + 1);
      } else {
        await handleSubmit();
      }
    } catch (error) {
      // Validation error – stay on current step
    }
  };

  const handlePrev = () => {
    setCurrentStep((s) => s - 1);
  };

  const handleSubmit = async () => {
    try {
      await form.validateFields(['project_name', 'client_name']);
      const values = form.getFieldsValue(true);
      setLoading(true);

      const data = await fetchWithAuth('/projects/', {
        method: 'POST',
        body: JSON.stringify(values),
      });

      message.success(`Project ${data.project_code} created successfully!`);
      form.resetFields();
      setCurrentStep(0);
      onSuccess(data);
    } catch (error) {
      console.error('Error creating project:', error);
      message.error(error.message || 'Error creating project');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    setCurrentStep(0);
    onCancel();
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <Form.Item
            name="project_name"
            label="Project Name"
            rules={[{ required: true, message: 'Please enter a project name' }]}
          >
            <Input placeholder="e.g., City Centre Tower Construction" size="large" />
          </Form.Item>
        );

      case 1:
        return (
          <>
            <Form.Item
              name="client_name"
              label="Client Name"
              rules={[{ required: true, message: 'Please enter client name' }]}
            >
              <Input placeholder="e.g., Al-Mansour Holdings" size="large" />
            </Form.Item>

            <Form.Item name="client_contact" label="Client Contact">
              <Input placeholder="Phone number" size="large" />
            </Form.Item>

            <Form.Item
              name="client_email"
              label="Client Email"
              rules={[{ type: 'email', message: 'Please enter a valid email' }]}
            >
              <Input placeholder="client@example.com" size="large" />
            </Form.Item>
          </>
        );

      case 2:
        return (
          <Form.Item name="description" label="Project Description">
            <TextArea
              rows={6}
              placeholder="Describe the project scope, objectives, and key deliverables..."
            />
          </Form.Item>
        );

      default:
        return null;
    }
  };

  return (
    <Modal
      title="Create New Project"
      open={visible}
      onCancel={handleCancel}
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button onClick={currentStep === 0 ? handleCancel : handlePrev}>
            {currentStep === 0 ? 'Cancel' : 'Previous'}
          </Button>
          <Button type="primary" loading={loading} onClick={handleNext}>
            {currentStep === steps.length - 1 ? 'Create Project' : 'Next'}
          </Button>
        </div>
      }
      width={600}
    >
      <Steps
        current={currentStep}
        style={{ marginBottom: 24 }}
        items={steps.map((s) => ({ title: s.title, icon: s.icon }))}
      />

      <Form form={form} layout="vertical" name="create_project_form">
        {renderStepContent()}
      </Form>
    </Modal>
  );
};

export default CreateProjectModal;
