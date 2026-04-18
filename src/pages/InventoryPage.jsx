import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, InputNumber, message, Button, Spin } from 'antd'; // UI Components
import '../styles/inventoryPage.css'; // Keep your styling
import { 
  BiBox, BiSearch, BiFilter, BiPlus, 
  BiError, BiCheckCircle, BiTrendingDown, 
  BiWrench, BiTrash
} from 'react-icons/bi';

import { inventoryService } from '../services';

const { Option } = Select;

const InventoryPage = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("All");
  const [searchTerm, setSearchTerm] = useState("");
  
  // Modal State
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();

  // --- 1. FETCH DATA FROM BACKEND ---
  const fetchData = async () => {
    setLoading(true);
    try {
      const data = await inventoryService.getAll();
      // Ensure data is an array
      setItems(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Fetch Error:", error);
      message.error("Failed to load inventory.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // --- 2. HANDLE ADD ITEM ---
  const handleAddItem = async () => {
    try {
      const values = await form.validateFields();
      
      // Prepare payload matching Backend Model
      const payload = {
        name: values.name,
        category: values.category,
        stock: values.stock,
        unit: values.unit,
        price: values.price,
        supplier: values.supplier, // Using supplier as location/source
        status: values.stock === 0 ? "Out of Stock" : values.stock < 10 ? "Low Stock" : "In Stock"
      };

      await inventoryService.create(payload);
      message.success("Item added successfully!");
      setIsModalVisible(false);
      form.resetFields();
      fetchData(); // Refresh table
    } catch (error) {
      message.error("Failed to add item. Check fields.");
    }
  };

  // --- 3. HANDLE DELETE ---
  const handleDelete = async (uid) => {
    if(!window.confirm("Are you sure you want to delete this item?")) return;
    try {
      await inventoryService.deleteById(uid);
      message.success("Item deleted");
      fetchData();
    } catch (error) {
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
        <button className="add-item-btn" onClick={() => setIsModalVisible(true)}>
          <BiPlus /> Add New Item
        </button>
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

      {/* --- INVENTORY TABLE --- */}
      <div className="table-container">
        {loading ? <div style={{textAlign:'center', padding: 20}}>Loading Inventory...</div> : (
          <table className="inventory-table">
            <thead>
              <tr>
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
                  <td colSpan="7" className="no-data">No items found.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* --- ADD ITEM MODAL --- */}
      <Modal 
        title="Add New Inventory Item" 
        open={isModalVisible} 
        onCancel={() => setIsModalVisible(false)} 
        onOk={handleAddItem}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Item Name" rules={[{ required: true, message: 'Please enter item name' }]}>
            <Input placeholder="e.g. Portland Cement" />
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
        </Form>
      </Modal>

    </div>
  );
};

export default InventoryPage;