import React, { useState, useEffect } from 'react';
import {
  Modal, Form, Input, Select, InputNumber, message, Button, Spin,
  Card, Row, Col, Tag, Typography, Upload, Space,
} from 'antd';
import {
  AppstoreOutlined, BarsOutlined, PlusOutlined,
} from '@ant-design/icons';
import '../styles/inventoryPage.css';
import { 
  BiBox, BiSearch, BiFilter, BiPlus, 
  BiError, BiCheckCircle, BiTrendingDown, 
  BiWrench, BiTrash
} from 'react-icons/bi';

import { inventoryService, projectService, siteService } from '../services';
import { getContracts } from '../services/contractService';

const { Option } = Select;
const { Text } = Typography;

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const InventoryPage = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("All");
  const [searchTerm, setSearchTerm] = useState("");
  const [viewMode, setViewMode] = useState("table");

  // Project / Contract / Site data for the form
  const [projects, setProjects] = useState([]);
  const [contracts, setContracts] = useState([]);
  const [sites, setSites] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);

  // Modal State
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();

  // --- 1. FETCH DATA FROM BACKEND ---
  const fetchData = async () => {
    setLoading(true);
    try {
      const data = await inventoryService.getAll();
      setItems(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Fetch Error:", error);
      message.error("Failed to load inventory.");
    } finally {
      setLoading(false);
    }
  };

  const fetchProjects = async () => {
    try {
      const data = await projectService.getAll();
      setProjects(Array.isArray(data) ? data : data?.projects || []);
    } catch {
      // non-critical
    }
  };

  const fetchSites = async (projectId) => {
    try {
      const data = await siteService.getAll();
      const all = Array.isArray(data) ? data : data?.sites || [];
      setSites(projectId ? all.filter(s => s.project_id === projectId) : all);
    } catch {
      // non-critical
    }
  };

  const fetchContracts = async (projectId) => {
    try {
      const data = await getContracts(projectId ? { project_id: projectId } : {});
      const all = Array.isArray(data) ? data : data?.items || data?.contracts || [];
      setContracts(all);
    } catch {
      // non-critical
    }
  };

  useEffect(() => {
    fetchData();
    fetchProjects();
    fetchContracts();
    fetchSites();
  }, []);

  const handleProjectChange = (projectId) => {
    setSelectedProjectId(projectId);
    form.setFieldsValue({ contract_id: undefined, site_id: undefined });
    fetchContracts(projectId);
    fetchSites(projectId);
  };

  // --- 2. HANDLE ADD ITEM ---
  const handleAddItem = async () => {
    try {
      const values = await form.validateFields();
      
      const payload = {
        name: values.name,
        category: values.category,
        stock: values.stock,
        unit: values.unit,
        price: values.price,
        supplier: values.supplier,
        status: values.stock === 0 ? "Out of Stock" : values.stock < 10 ? "Low Stock" : "In Stock",
        project_id: values.project_id,
        contract_id: values.contract_id,
        site_id: values.site_id,
      };

      const created = await inventoryService.create(payload);
      const newUid = created?.uid;

      // Upload images if any (best-effort, non-blocking)
      const fileList = values.images?.fileList || [];
      if (newUid && fileList.length > 0) {
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        for (const fileItem of fileList) {
          if (fileItem.originFileObj) {
            const formData = new FormData();
            formData.append('file', fileItem.originFileObj);
            try {
              await fetch(`${API_BASE}/inventory/${newUid}/photos`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
                body: formData,
              });
            } catch {
              // photo upload is best-effort
            }
          }
        }
      }

      message.success("Item added successfully!");
      setIsModalVisible(false);
      form.resetFields();
      setSelectedProjectId(null);
      fetchData();
    } catch {
      message.error("Failed to add item. Check required fields.");
    }
  };

  // --- 3. HANDLE DELETE ---
  const handleDelete = async (uid) => {
    if(!window.confirm("Are you sure you want to delete this item?")) return;
    try {
      await inventoryService.deleteById(uid);
      message.success("Item deleted");
      fetchData();
    } catch {
      message.error("Delete failed");
    }
  };

  // --- STATS CALCULATION ---
  const totalItems = items.length;
  const lowStockItems = items.filter(item => item.status === "Low Stock" || item.status === "Out of Stock").length;
  const categories = [...new Set(items.map(item => item.category))].length;

  // --- FILTERING LOGIC ---
  const filteredItems = items.filter(item => {
    const matchesCategory = filter === "All" || item.category === filter;
    const matchesSearch = item.name.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  // --- HELPER FOR STATUS BADGE ---
  const getStatusDisplay = (status) => {
    if (status === "Out of Stock") return { class: "out-stock", icon: <BiError /> };
    if (status === "Low Stock") return { class: "low-stock", icon: <BiTrendingDown /> };
    return { class: "in-stock", icon: <BiCheckCircle /> };
  };

  return (
    <div className="inventory-container">
      {/* --- HEADER --- */}
      <div className="inventory-header">
        <div>
          <h2><BiBox className="header-icon" /> Inventory Management</h2>
          <p>Track materials, tools, and machinery across all sites.</p>
        </div>
        <Space>
          <Button
            icon={<BarsOutlined />}
            type={viewMode === 'table' ? 'primary' : 'default'}
            onClick={() => setViewMode('table')}
          />
          <Button
            icon={<AppstoreOutlined />}
            type={viewMode === 'grid' ? 'primary' : 'default'}
            onClick={() => setViewMode('grid')}
          />
          <button className="add-item-btn" onClick={() => setIsModalVisible(true)}>
            <BiPlus /> Add New Item
          </button>
        </Space>
      </div>

      {/* --- STATS CARDS --- */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-icon blue"><BiBox /></div>
          <div className="stat-info">
            <h3>{totalItems}</h3>
            <span>Total SKU Items</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red"><BiError /></div>
          <div className="stat-info">
            <h3>{lowStockItems}</h3>
            <span>Low/Out Stock Alerts</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon orange"><BiWrench /></div>
          <div className="stat-info">
            <h3>{categories}</h3>
            <span>Active Categories</span>
          </div>
        </div>
      </div>

      {/* --- CONTROLS ROW --- */}
      <div className="controls-row">
        <div className="search-wrapper">
          <BiSearch className="search-icon" />
          <input 
            type="text" 
            placeholder="Search item name..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filter-wrapper">
          <BiFilter className="filter-icon" />
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="All">All Categories</option>
            <option value="Material">Materials</option>
            <option value="Tool">Tools</option>
            <option value="Machinery">Machinery</option>
            <option value="Safety">Safety Gear</option>
          </select>
        </div>
      </div>

      {/* --- GRID VIEW --- */}
      {viewMode === 'grid' && (
        <div style={{ marginTop: 16 }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
          ) : (
            <Row gutter={[16, 16]}>
              {filteredItems.map(item => {
                const statusInfo = getStatusDisplay(item.status);
                return (
                  <Col xs={24} sm={12} md={8} lg={6} key={item.uid}>
                    <Card
                      hoverable
                      cover={
                        item.image_urls?.[0] ? (
                          <img
                            src={`${API_BASE}${item.image_urls[0]}`}
                            alt={item.name}
                            style={{ height: 200, objectFit: 'cover', width: '100%' }}
                          />
                        ) : (
                          <div style={{ height: 200, background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <BiBox size={48} color="#ccc" />
                          </div>
                        )
                      }
                      actions={[
                        <button
                          key="delete"
                          onClick={() => handleDelete(item.uid)}
                          style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'red' }}
                        >
                          <BiTrash />
                        </button>,
                      ]}
                    >
                      <Card.Meta
                        title={item.name}
                        description={
                          <>
                            <Tag color="blue">{item.category}</Tag>
                            <div style={{ marginTop: 8 }}>
                              <Text strong style={{ fontSize: 16, color: '#1890ff' }}>${item.price}</Text>
                              <div style={{ fontSize: 12, color: '#888' }}>
                                Stock: {item.stock} {item.unit}
                              </div>
                              <span className={`status-pill ${statusInfo.class}`} style={{ fontSize: 11 }}>
                                {statusInfo.icon} {item.status}
                              </span>
                            </div>
                          </>
                        }
                      />
                    </Card>
                  </Col>
                );
              })}
              {filteredItems.length === 0 && (
                <Col span={24}><div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No items found.</div></Col>
              )}
            </Row>
          )}
        </div>
      )}

      {/* --- TABLE VIEW --- */}
      {viewMode === 'table' && (
        <div className="table-container">
          {loading ? <div style={{textAlign:'center', padding: 20}}>Loading Inventory...</div> : (
            <table className="inventory-table">
              <thead>
                <tr>
                  <th>Photo</th>
                  <th>Item Name</th>
                  <th>Category</th>
                  <th>Stock Level</th>
                  <th>Status</th>
                  <th>Unit Price</th>
                  <th>Location/Supplier</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.length > 0 ? (
                  filteredItems.map(item => {
                    const statusInfo = getStatusDisplay(item.status);
                    return (
                      <tr key={item.uid}>
                        <td style={{ width: 56 }}>
                          {item.image_urls?.[0] ? (
                            <img
                              src={`${API_BASE}${item.image_urls[0]}`}
                              alt={item.name}
                              style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 4 }}
                            />
                          ) : (
                            <div style={{ width: 48, height: 48, background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 4 }}>
                              <BiBox color="#ccc" />
                            </div>
                          )}
                        </td>
                        <td className="item-name-cell">
                          <strong>{item.name}</strong>
                        </td>
                        <td>
                          <span className="category-badge">{item.category}</span>
                        </td>
                        <td>
                          <span className="stock-count">
                            {item.stock} <small>{item.unit}</small>
                          </span>
                        </td>
                        <td>
                          <span className={`status-pill ${statusInfo.class}`}>
                            {statusInfo.icon} {item.status}
                          </span>
                        </td>
                        <td>${item.price}</td>
                        <td className="location-cell">{item.supplier || "N/A"}</td>
                        <td>
                          <button className="delete-icon-btn" onClick={() => handleDelete(item.uid)} style={{border:'none', background:'transparent', cursor:'pointer', color:'red'}}>
                              <BiTrash />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan="8" className="no-data">No items found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* --- ADD ITEM MODAL --- */}
      <Modal 
        title="Add New Inventory Item" 
        open={isModalVisible} 
        onCancel={() => { setIsModalVisible(false); form.resetFields(); setSelectedProjectId(null); }} 
        onOk={handleAddItem}
        width={560}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Item Name" rules={[{ required: true, message: 'Please enter item name' }]}>
            <Input placeholder="e.g. Portland Cement" />
          </Form.Item>

          <Form.Item name="project_id" label="Project" rules={[{ required: true, message: 'Project is required' }]}>
            <Select placeholder="Select Project" onChange={handleProjectChange}>
              {projects.map(p => (
                <Option key={p.uid || p.id} value={p.uid || p.id}>{p.name || p.project_name}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="contract_id" label="Contract" rules={[{ required: true, message: 'Contract is required' }]}>
            <Select placeholder="Select Contract">
              {contracts.map(c => (
                <Option key={c.uid} value={c.uid}>{c.contract_code} – {c.contract_name}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="site_id" label="Site" rules={[{ required: true, message: 'Site is required' }]}>
            <Select placeholder="Select Site">
              {sites.map(s => (
                <Option key={s.uid || s.id} value={s.uid || s.id}>{s.name || s.site_name}</Option>
              ))}
            </Select>
          </Form.Item>
          
          <div style={{display:'flex', gap: 10}}>
             <Form.Item name="category" label="Category" style={{flex:1}} rules={[{ required: true }]}>
               <Select placeholder="Select">
                 <Option value="Material">Material</Option>
                 <Option value="Tool">Tool</Option>
                 <Option value="Machinery">Machinery</Option>
                 <Option value="Safety">Safety</Option>
               </Select>
             </Form.Item>
             <Form.Item name="unit" label="Unit" style={{flex:1}} rules={[{ required: true }]}>
               <Select placeholder="Select">
                 <Option value="pcs">Pieces</Option>
                 <Option value="kg">Kg</Option>
                 <Option value="bags">Bags</Option>
                 <Option value="tons">Tons</Option>
                 <Option value="liters">Liters</Option>
               </Select>
             </Form.Item>
          </div>

          <div style={{display:'flex', gap: 10}}>
             <Form.Item name="stock" label="Initial Stock" style={{flex:1}} rules={[{ required: true }]}>
                <InputNumber style={{width:'100%'}} min={0} />
             </Form.Item>
             <Form.Item name="price" label="Unit Price" style={{flex:1}} rules={[{ required: true }]}>
                <InputNumber style={{width:'100%'}} prefix="$" min={0} />
             </Form.Item>
          </div>

          <Form.Item name="supplier" label="Location / Supplier">
            <Input placeholder="e.g. Warehouse A" />
          </Form.Item>

          <Form.Item name="images" label="Product Photos">
            <Upload
              listType="picture-card"
              beforeUpload={() => false}
              multiple
              maxCount={5}
            >
              <div>
                <PlusOutlined />
                <div style={{ marginTop: 8 }}>Upload</div>
              </div>
            </Upload>
          </Form.Item>
        </Form>
      </Modal>

    </div>
  );
};

export default InventoryPage;