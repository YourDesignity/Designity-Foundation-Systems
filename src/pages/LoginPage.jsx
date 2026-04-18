import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Form,
  Input,
  Button,
  Checkbox,
  message,
  Tabs,
} from "antd";
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
  HomeOutlined,
  KeyOutlined,
} from "@ant-design/icons";
import { useMutation } from "@tanstack/react-query";
import { useAuth } from "../context/AuthContext";
import axios from "axios";
import "../styles/LoginPage.css";

const API_BASE_URL = "http://127.0.0.1:8000";

const LoginPage = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [rememberMe, setRememberMe] = useState(false);
  const [activeTab, setActiveTab] = useState("login");

  const [form] = Form.useForm();
  const [registerForm] = Form.useForm();

  // Load saved credentials on mount
  useEffect(() => {
    const savedEmail = localStorage.getItem("montreal_email");
    const savedPassword = localStorage.getItem("montreal_password");
    const savedRemember = localStorage.getItem("montreal_remember");

    if (savedRemember === "true" && savedEmail && savedPassword) {
      setRememberMe(true);
      form.setFieldsValue({
        email: savedEmail,
        password: atob(savedPassword),
      });
    }
  }, [form]);

  const loginMutation = useMutation({
    mutationFn: ({ email, password }) => login(email, password),
    onSuccess: (_, variables) => {
      if (rememberMe) {
        localStorage.setItem("montreal_email", variables.email);
        localStorage.setItem("montreal_password", btoa(variables.password));
        localStorage.setItem("montreal_remember", "true");
      } else {
        localStorage.removeItem("montreal_email");
        localStorage.removeItem("montreal_password");
        localStorage.removeItem("montreal_remember");
      }
      message.success("Login successful!");
      navigate("/dashboard");
    },
    onError: (error) => {
      message.error(error.message || "Failed to log in.");
    },
  });

  const registerMutation = useMutation({
    mutationFn: (values) =>
      axios.post(`${API_BASE_URL}/auth/register-admin`, {
        email: values.email,
        password: values.password,
        full_name: values.full_name,
        company_name: values.company_name,
        setup_key: values.setup_key,
      }),
    onSuccess: () => {
      message.success("SuperAdmin registered successfully! Please login.");
      registerForm.resetFields();
      setActiveTab("login");
    },
    onError: (error) => {
      const errorMsg = error.response?.data?.detail || "Registration failed";
      message.error(errorMsg);
    },
  });

  const onFinish = (values) => {
    loginMutation.mutate({ email: values.email, password: values.password });
  };

  const handleRegister = (values) => {
    registerMutation.mutate(values);
  };

  const tabItems = [
    {
      key: "login",
      label: "Sign In",
      children: (
        <Form form={form} name="login" onFinish={onFinish} layout="vertical" className="login-form">
          <Form.Item
            name="email"
            rules={[
              { required: true, message: "Please enter your email" },
              { type: "email", message: "Please enter a valid email" },
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="Email"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: "Please enter your password" }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Password"
              size="large"
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 16 }}>
            <Checkbox
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            >
              Remember me
            </Checkbox>
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loginMutation.isPending}
              block
              size="large"
              className="login-btn"
            >
              SIGN IN
            </Button>
          </Form.Item>
        </Form>
      ),
    },
    {
      key: "register",
      label: "Register",
      children: (
        <Form
          form={registerForm}
          name="register"
          onFinish={handleRegister}
          layout="vertical"
          className="login-form"
        >
          <Form.Item
            name="full_name"
            rules={[{ required: true, message: "Please enter your full name" }]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="Full Name"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="email"
            rules={[
              { required: true, message: "Please enter your email" },
              { type: "email", message: "Please enter a valid email" },
            ]}
          >
            <Input
              prefix={<MailOutlined />}
              placeholder="Email"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="company_name"
            rules={[
              { required: true, message: "Please enter company name" },
            ]}
          >
            <Input
              prefix={<HomeOutlined />}
              placeholder="Company Name"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[
              { required: true, message: "Please enter a password" },
              { min: 6, message: "Password must be at least 6 characters" },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Password"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="confirm_password"
            dependencies={["password"]}
            rules={[
              { required: true, message: "Please confirm your password" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue("password") === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(
                    new Error("Passwords do not match")
                  );
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Confirm Password"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="setup_key"
            rules={[
              { required: true, message: "Please enter the setup key" },
            ]}
          >
            <Input
              prefix={<KeyOutlined />}
              placeholder="Setup Key"
              size="large"
            />
          </Form.Item>

          <Form.Item style={{ marginTop: 8 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={registerMutation.isPending}
              block
              size="large"
              className="login-btn"
            >
              Register SuperAdmin
            </Button>
          </Form.Item>
        </Form>
      ),
    },
  ];

  return (
    <div className="login-container">
      {/* Animated Background */}
      <div className="animated-bg">
        <div className="bg-gradient gradient-1"></div>
        <div className="bg-gradient gradient-2"></div>
        <div className="bg-gradient gradient-3"></div>
      </div>

      {/* Login Card */}
      <div className="login-card">
        <div className="login-header">
          <h1 className="login-title">Montreal International</h1>
          <p className="login-subtitle">Payroll &amp; Workforce Management System</p>
        </div>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          centered
          className="login-tabs"
          items={tabItems}
        />
      </div>
    </div>
  );
};

export default LoginPage;
