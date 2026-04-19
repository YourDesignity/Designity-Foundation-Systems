/**
 * LoginPage.jsx — Redesigned
 * Split-screen layout: brand panel left, clean form right.
 * Matches the Designity × Montreal International identity.
 * All auth logic preserved exactly.
 */

import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Form, Input, Button, Checkbox, message, Tabs } from "antd";
import {
  UserOutlined, LockOutlined, MailOutlined,
  HomeOutlined, KeyOutlined, ArrowRightOutlined,
} from "@ant-design/icons";
import { useMutation } from "@tanstack/react-query";
import { useAuth } from "../context/AuthContext";
import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:8000";

// ── Inline styles — no external CSS dependency ────────────────────────────────
const S = {
  page: {
    display: 'flex',
    height: '100vh',
    overflow: 'hidden',
    fontFamily: "'Inter', 'Segoe UI', Arial, sans-serif",
    background: '#f8fafc',
  },
  // ── Left brand panel ──────────────────────────────────────────────────────
  left: {
    width: '42%',
    minWidth: 340,
    background: 'linear-gradient(160deg, #1E3A5F 0%, #2E75B6 60%, #1a9da3 100%)',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    padding: '44px 48px 36px',
    position: 'relative',
    overflow: 'hidden',
    flexShrink: 0,
  },
  // Decorative geometric rings
  ring1: {
    position: 'absolute', borderRadius: '50%',
    border: '1px solid rgba(255,255,255,0.08)',
    width: 420, height: 420, top: -80, right: -120,
  },
  ring2: {
    position: 'absolute', borderRadius: '50%',
    border: '1px solid rgba(255,255,255,0.06)',
    width: 600, height: 600, top: -180, right: -220,
  },
  ring3: {
    position: 'absolute', borderRadius: '50%',
    border: '1px solid rgba(255,255,255,0.05)',
    width: 280, height: 280, bottom: 60, left: -80,
  },
  ring4: {
    position: 'absolute', borderRadius: '50%',
    border: '1px solid rgba(255,255,255,0.06)',
    width: 160, height: 160, bottom: 120, right: 40,
  },
  // Dot grid pattern overlay
  dots: {
    position: 'absolute', inset: 0,
    backgroundImage: 'radial-gradient(rgba(255,255,255,0.07) 1px, transparent 1px)',
    backgroundSize: '28px 28px',
    pointerEvents: 'none',
  },
  logoRow: {
    display: 'flex', alignItems: 'center', gap: 10, position: 'relative', zIndex: 2,
  },
  logoIcon: {
    width: 40, height: 40, borderRadius: 10,
    background: 'rgba(255,255,255,0.15)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 20, fontWeight: 800, color: '#fff',
    border: '1px solid rgba(255,255,255,0.25)',
  },
  logoText: {
    fontSize: 16, fontWeight: 700, color: '#fff',
    lineHeight: 1.2,
  },
  logoSub: {
    fontSize: 11, color: 'rgba(255,255,255,0.6)', fontWeight: 400,
  },
  // Illustration area
  illustrationWrap: {
    flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
    position: 'relative', zIndex: 2,
    paddingTop: 12,
    paddingBottom: 12,
  },
  // Central brand message
  brandBlock: {
    position: 'relative', zIndex: 2,
  },
  brandTitle: {
    fontSize: 32, fontWeight: 800, color: '#fff',
    lineHeight: 1.25, marginBottom: 14, letterSpacing: '-0.5px',
  },
  brandSub: {
    fontSize: 14, color: 'rgba(255,255,255,0.7)',
    lineHeight: 1.7, maxWidth: 300,
  },
  pillRow: {
    display: 'flex', gap: 8, marginTop: 24, flexWrap: 'wrap',
  },
  pill: {
    fontSize: 11, fontWeight: 600,
    padding: '5px 12px', borderRadius: 20,
    background: 'rgba(255,255,255,0.12)',
    color: 'rgba(255,255,255,0.85)',
    border: '1px solid rgba(255,255,255,0.18)',
    letterSpacing: '0.3px',
  },
  footer: {
    fontSize: 12, color: 'rgba(255,255,255,0.45)',
    position: 'relative', zIndex: 2,
  },
  // ── Right form panel ──────────────────────────────────────────────────────
  right: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0 48px',
    background: '#fff',
    overflowY: 'auto',
  },
  formWrap: {
    width: '100%',
    maxWidth: 420,
    paddingTop: 0,
  },
  greeting: {
    fontSize: 28, fontWeight: 800, color: '#1E3A5F',
    marginBottom: 6, letterSpacing: '-0.5px',
  },
  greetingSub: {
    fontSize: 14, color: '#6b7280', marginBottom: 28,
  },
  inputStyle: {
    height: 46,
    borderRadius: 8,
    fontSize: 14,
    border: '1.5px solid #e5e7eb',
    display: 'flex',
    alignItems: 'center',
    lineHeight: '44px',
  },
  btnPrimary: {
    height: 48, borderRadius: 8, fontSize: 15,
    fontWeight: 700, letterSpacing: '0.3px',
    background: 'linear-gradient(135deg, #1E3A5F 0%, #2E75B6 100%)',
    border: 'none',
    boxShadow: '0 4px 14px rgba(30,58,95,0.25)',
  },
  divider: {
    display: 'flex', alignItems: 'center', gap: 12,
    margin: '20px 0', color: '#9ca3af', fontSize: 12,
  },
  dividerLine: {
    flex: 1, height: 1, background: '#e5e7eb',
  },
  pageFooter: {
    marginTop: 24, textAlign: 'center',
    fontSize: 12, color: '#9ca3af',
  },
};

// ── SVG Illustration — minimal isometric-style workforce/building ─────────────
const WorkforceIllustration = () => (
  <svg viewBox="0 0 320 280" fill="none" xmlns="http://www.w3.org/2000/svg"
    style={{ width: '100%', maxWidth: 300, opacity: 0.92 }}>

    {/* Building base */}
    <rect x="80" y="100" width="160" height="140" rx="4" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.18)" strokeWidth="1"/>

    {/* Building floors */}
    {[120, 145, 170, 195].map((y, i) => (
      <g key={i}>
        <rect x="96" y={y} width="28" height="18" rx="2" fill="rgba(255,255,255,0.12)" stroke="rgba(255,255,255,0.2)" strokeWidth="0.5"/>
        <rect x="134" y={y} width="28" height="18" rx="2" fill="rgba(255,255,255,0.12)" stroke="rgba(255,255,255,0.2)" strokeWidth="0.5"/>
        <rect x="172" y={y} width="28" height="18" rx="2" fill={i === 1 ? "rgba(79,172,254,0.35)" : "rgba(255,255,255,0.12)"} stroke="rgba(255,255,255,0.2)" strokeWidth="0.5"/>
      </g>
    ))}

    {/* Rooftop accent */}
    <rect x="80" y="92" width="160" height="14" rx="2" fill="rgba(255,255,255,0.15)" stroke="rgba(255,255,255,0.2)" strokeWidth="1"/>
    <rect x="145" y="78" width="30" height="20" rx="2" fill="rgba(255,255,255,0.1)" stroke="rgba(255,255,255,0.2)" strokeWidth="1"/>

    {/* Door */}
    <rect x="142" y="210" width="36" height="30" rx="3" fill="rgba(255,255,255,0.1)" stroke="rgba(255,255,255,0.25)" strokeWidth="1"/>

    {/* Left chart panel */}
    <rect x="14" y="70" width="58" height="80" rx="6" fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.15)" strokeWidth="1"/>
    {[0,1,2].map(i => (
      <rect key={i} x={20 + i*16} y={110 - i*12} width="10" height={20 + i*12} rx="2"
        fill={`rgba(255,255,255,${0.15 + i*0.08})`}/>
    ))}
    <text x="43" y="163" textAnchor="middle" fontSize="7" fill="rgba(255,255,255,0.5)" fontFamily="sans-serif">Revenue</text>

    {/* Right stats panel */}
    <rect x="248" y="70" width="58" height="80" rx="6" fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.15)" strokeWidth="1"/>
    <circle cx="277" cy="100" r="18" stroke="rgba(79,172,254,0.5)" strokeWidth="3" fill="none"/>
    <circle cx="277" cy="100" r="18" stroke="rgba(255,255,255,0.6)" strokeWidth="3" fill="none"
      strokeDasharray="28 86" strokeDashoffset="0"/>
    <text x="277" y="103" textAnchor="middle" fontSize="8" fill="rgba(255,255,255,0.8)" fontFamily="sans-serif" fontWeight="600">78%</text>
    <text x="277" y="158" textAnchor="middle" fontSize="7" fill="rgba(255,255,255,0.5)" fontFamily="sans-serif">Utilization</text>

    {/* People (3 figures) */}
    {[
      { x: 50, color: 'rgba(255,255,255,0.6)' },
      { x: 160, color: 'rgba(79,172,254,0.8)' },
      { x: 270, color: 'rgba(255,255,255,0.6)' },
    ].map((p, i) => (
      <g key={i}>
        <circle cx={p.x} cy="248" r="8" fill={p.color}/>
        <rect x={p.x - 7} y="256" width="14" height="14" rx="7" fill={p.color}/>
      </g>
    ))}

    {/* Connecting lines */}
    <line x1="58" y1="252" x2="152" y2="252" stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="3 4"/>
    <line x1="168" y1="252" x2="262" y2="252" stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="3 4"/>

    {/* Ground line */}
    <line x1="20" y1="242" x2="300" y2="242" stroke="rgba(255,255,255,0.08)" strokeWidth="1"/>
  </svg>
);

// ── Main Login Page ───────────────────────────────────────────────────────────
const LoginPage = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [rememberMe, setRememberMe] = useState(false);
  const [activeTab, setActiveTab] = useState("login");
  const [form] = Form.useForm();
  const [registerForm] = Form.useForm();

  useEffect(() => {
    const savedEmail    = localStorage.getItem("montreal_email");
    const savedPassword = localStorage.getItem("montreal_password");
    const savedRemember = localStorage.getItem("montreal_remember");
    if (savedRemember === "true" && savedEmail && savedPassword) {
      setRememberMe(true);
      form.setFieldsValue({ email: savedEmail, password: atob(savedPassword) });
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
    onError: (error) => { message.error(error.message || "Failed to log in."); },
  });

  const registerMutation = useMutation({
    mutationFn: (values) =>
      axios.post(`${API_BASE_URL}/auth/register-admin`, {
        email: values.email, password: values.password,
        full_name: values.full_name, company_name: values.company_name,
        setup_key: values.setup_key,
      }),
    onSuccess: () => {
      message.success("SuperAdmin registered successfully! Please login.");
      registerForm.resetFields();
      setActiveTab("login");
    },
    onError: (error) => {
      message.error(error.response?.data?.detail || "Registration failed");
    },
  });

  const inputProps = { style: S.inputStyle };

  const tabItems = [
    {
      key: "login",
      label: "Sign In",
      children: (
        <Form form={form} name="login" onFinish={(v) => loginMutation.mutate(v)} layout="vertical">
          <Form.Item name="email"
            rules={[{ required: true, message: "Email required" }, { type: "email", message: "Invalid email" }]}>
            <Input prefix={<UserOutlined style={{ color: '#9ca3af' }} />}
              placeholder="Email address" size="large" {...inputProps} />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: "Password required" }]}>
            <Input.Password prefix={<LockOutlined style={{ color: '#9ca3af' }} />}
              placeholder="Password" size="large" {...inputProps} />
          </Form.Item>
          <Form.Item style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Checkbox checked={rememberMe} onChange={e => setRememberMe(e.target.checked)}
                style={{ color: '#6b7280', fontSize: 13 }}>
                Remember me
              </Checkbox>
            </div>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit"
              loading={loginMutation.isPending} block size="large"
              style={S.btnPrimary} icon={<ArrowRightOutlined />}
              iconPosition="end">
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
        <Form form={registerForm} name="register" onFinish={(v) => registerMutation.mutate(v)} layout="vertical">
          {[
            { name: "full_name", placeholder: "Full Name", prefix: <UserOutlined style={{ color: '#9ca3af' }} />, rules: [{ required: true }] },
            { name: "email", placeholder: "Email", prefix: <MailOutlined style={{ color: '#9ca3af' }} />, rules: [{ required: true }, { type: "email" }] },
            { name: "company_name", placeholder: "Company Name", prefix: <HomeOutlined style={{ color: '#9ca3af' }} />, rules: [{ required: true }] },
          ].map(f => (
            <Form.Item key={f.name} name={f.name} rules={f.rules}>
              <Input prefix={f.prefix} placeholder={f.placeholder} size="large" {...inputProps} />
            </Form.Item>
          ))}
          <Form.Item name="password" rules={[{ required: true }, { min: 6 }]}>
            <Input.Password prefix={<LockOutlined style={{ color: '#9ca3af' }} />}
              placeholder="Password" size="large" {...inputProps} />
          </Form.Item>
          <Form.Item name="confirm_password"
            dependencies={["password"]}
            rules={[{ required: true }, ({ getFieldValue }) => ({
              validator(_, v) {
                return (!v || getFieldValue("password") === v)
                  ? Promise.resolve()
                  : Promise.reject(new Error("Passwords do not match"));
              },
            })]}>
            <Input.Password prefix={<LockOutlined style={{ color: '#9ca3af' }} />}
              placeholder="Confirm Password" size="large" {...inputProps} />
          </Form.Item>
          <Form.Item name="setup_key" rules={[{ required: true }]}>
            <Input prefix={<KeyOutlined style={{ color: '#9ca3af' }} />}
              placeholder="Setup Key" size="large" {...inputProps} />
          </Form.Item>
          <Form.Item style={{ marginTop: 8 }}>
            <Button type="primary" htmlType="submit"
              loading={registerMutation.isPending} block size="large"
              style={S.btnPrimary}>
              Register SuperAdmin
            </Button>
          </Form.Item>
        </Form>
      ),
    },
  ];

  return (
    <div style={S.page}>
      {/* Input vertical alignment fix for Ant Design v6 */}
      <style>{`
        .montreal-login .ant-input-affix-wrapper {
          padding-top: 0 !important;
          padding-bottom: 0 !important;
          display: flex !important;
          align-items: center !important;
        }
        .montreal-login .ant-input-affix-wrapper input.ant-input {
          line-height: 44px !important;
          height: 44px !important;
          padding-top: 0 !important;
          padding-bottom: 0 !important;
        }
        .montreal-login .ant-input-prefix {
          display: flex !important;
          align-items: center !important;
          margin-right: 8px !important;
        }
        .montreal-login .ant-tabs-tab {
          font-size: 14px !important;
          padding: 8px 0 !important;
        }
        .montreal-login .ant-form-item {
          margin-bottom: 16px !important;
        }
      `}</style>
      {/* ── Left brand panel ───────────────────────────────────────────────── */}
      <div style={S.left}>
        {/* Decorative rings */}
        <div style={S.ring1} />
        <div style={S.ring2} />
        <div style={S.ring3} />
        <div style={S.ring4} />
        <div style={S.dots} />

        {/* Logo */}
        <div style={S.logoRow}>
          <div style={S.logoIcon}>D</div>
          <div>
            <div style={S.logoText}>Designity × Montreal</div>
            <div style={S.logoSub}>Enterprise Workforce Platform</div>
          </div>
        </div>

        {/* Illustration */}
        <div style={S.illustrationWrap}>
          <WorkforceIllustration />
        </div>

        {/* Brand copy */}
        <div style={S.brandBlock}>
          <div style={S.brandTitle}>
            Powering Workforce<br />Operations Across<br />the Gulf
          </div>
          <div style={S.brandSub}>
            Complete payroll, project management, and workforce analytics — built for Kuwait and the GCC.
          </div>
          <div style={S.pillRow}>
            {['HR & Payroll', 'Projects', 'Contracts', 'Fleet', 'Finance'].map(t => (
              <span key={t} style={S.pill}>{t}</span>
            ))}
          </div>
        </div>

        <div style={S.footer}>© 2026 Designity. All rights reserved.</div>
      </div>

      {/* ── Right form panel ───────────────────────────────────────────────── */}
      <div style={S.right}>
        <div style={S.formWrap} className="montreal-login">
          <div style={S.greeting}>
            {activeTab === 'login' ? 'Welcome back' : 'Get started'}
          </div>
          <div style={S.greetingSub}>
            {activeTab === 'login'
              ? 'Sign in to your Montreal International account'
              : 'Register a new SuperAdmin account'}
          </div>

          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems}
            style={{ marginBottom: 0 }}
          />

          <div style={S.pageFooter}>
            Secured by Designity &nbsp;·&nbsp; Montreal International
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
