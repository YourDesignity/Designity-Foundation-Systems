import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BiPlus, BiTrash, BiTime } from 'react-icons/bi';
import { getEmployees } from '../services/apiService'; 
import '../styles/projectsPage.css';

const OvertimePage = () => {
  // --- STATE ---
  const [employees, setEmployees] = useState([]);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Default to current month
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });

  const [formData, setFormData] = useState({
    employee_id: '',
    date: new Date().toISOString().split('T')[0],
    hours: '',
    type: 'Normal', 
    reason: ''
  });

  // --- AUTH HEADER ---
  const getAuthHeaders = () => {
    let token = localStorage.getItem('access_token') || localStorage.getItem('token');
    if (token && token.startsWith('"')) token = token.slice(1, -1);
    return { headers: { 'Authorization': `Bearer ${token}` } };
  };

  // --- 1. INITIAL LOAD ---
  useEffect(() => {
    fetchEmployees();
  }, []);

  useEffect(() => {
    fetchOvertimeRecords();
  }, [selectedMonth]);

  const fetchEmployees = async () => {
    try {
      const data = await getEmployees();
      setEmployees(data);
    } catch (err) { console.error("Failed to load employees"); }
  };

  const fetchOvertimeRecords = async () => {
    const [year, month] = selectedMonth.split('-');
    try {
      const res = await axios.get(`http://localhost:8000/overtime/${year}/${month}`, getAuthHeaders());
      setRecords(res.data);
    } catch (err) { console.error("Failed to load OT records"); }
  };

  // --- 2. SUBMIT OVERTIME ---
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.employee_id || !formData.hours) return alert("Please fill required fields");

    setLoading(true);
    
    // IMPORTANT: Convert types to match Backend Schema
    const payload = {
        ...formData,
        employee_id: parseInt(formData.employee_id),
        hours: parseFloat(formData.hours)
    };

    try {
      await axios.post('http://localhost:8000/overtime/', payload, getAuthHeaders());
      
      // Reset form (keep date, clear values)
      setFormData({ ...formData, hours: '', reason: '' }); 
      fetchOvertimeRecords();
      alert("Overtime Added Successfully!");
    } catch (error) {
      console.error(error);
      alert("Failed to add overtime. Ensure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  // --- 3. DELETE OVERTIME ---
  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this record?")) return;
    try {
      await axios.delete(`http://localhost:8000/overtime/${id}`, getAuthHeaders());
      fetchOvertimeRecords();
    } catch (err) { alert("Delete failed"); }
  };

  return (
    <div style={{ padding: '20px', background: '#f4f5f7', minHeight: '100vh' }}>
      
      {/* HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
            <h2 style={{ margin: 0, color: '#172b4d' }}>Overtime Management</h2>
            <p style={{ margin: 0, color: '#6b778c', fontSize: '14px' }}>Log extra hours for payroll calculation</p>
        </div>
        <input 
          type="month" value={selectedMonth} 
          onChange={(e) => setSelectedMonth(e.target.value)}
          style={{ padding: '8px', borderRadius: '5px', border: '1px solid #ddd' }}
        />
      </div>

      <div style={{ display: 'flex', gap: '20px', flexDirection: 'row', flexWrap: 'wrap' }}>
        
        {/* LEFT: FORM */}
        <div style={{ flex: '1 1 300px', background: 'white', padding: '25px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)', height: 'fit-content' }}>
          <h3 style={{ marginTop: 0, color: '#4c35de', display:'flex', alignItems:'center', gap:'10px' }}><BiPlus /> Add Overtime</h3>
          
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            
            <div>
              <label style={labelStyle}>Employee</label>
              <select 
                style={inputStyle} 
                value={formData.employee_id}
                onChange={(e) => setFormData({...formData, employee_id: e.target.value})}
                required
              >
                <option value="">Select Employee...</option>
                {employees.map(emp => (
                  <option key={emp.id || emp.uid} value={emp.id || emp.uid}>{emp.name}</option>
                ))}
              </select>
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <div style={{ flex: 1 }}>
                <label style={labelStyle}>Date</label>
                <input 
                  type="date" style={inputStyle} value={formData.date}
                  onChange={(e) => setFormData({...formData, date: e.target.value})}
                  required
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={labelStyle}>Hours</label>
                <input 
                  type="number" step="0.5" min="0.5" style={inputStyle} value={formData.hours}
                  onChange={(e) => setFormData({...formData, hours: e.target.value})}
                  placeholder="2.5" required
                />
              </div>
            </div>

            <div>
              <label style={labelStyle}>Type (Multiplier)</label>
              <select 
                style={inputStyle} value={formData.type}
                onChange={(e) => setFormData({...formData, type: e.target.value})}
              >
                <option value="Normal">Normal Day (1.0x)</option>
                <option value="Offday">Off Day / Holiday (1.5x)</option>
              </select>
            </div>

            <div>
              <label style={labelStyle}>Reason (Optional)</label>
              <input 
                type="text" style={inputStyle} value={formData.reason}
                onChange={(e) => setFormData({...formData, reason: e.target.value})}
                placeholder="e.g. Urgent site work"
              />
            </div>

            <button 
              type="submit" disabled={loading}
              style={{ background: '#4c35de', color: 'white', padding: '12px', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight:'bold', marginTop: '10px' }}
            >
              {loading ? 'Saving...' : 'Add Record'}
            </button>
          </form>
        </div>

        {/* RIGHT: TABLE */}
        <div style={{ flex: '2 1 500px', background: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' }}>
          <h3 style={{ marginTop: 0, marginBottom:'15px', color: '#172b4d' }}>Records for {selectedMonth}</h3>
          
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f4f5f7', textAlign: 'left', color: '#5e6c84', fontSize:'13px', textTransform:'uppercase' }}>
                <th style={{ padding: '12px' }}>Date</th>
                <th style={{ padding: '12px' }}>Employee</th>
                <th style={{ padding: '12px' }}>Hours</th>
                <th style={{ padding: '12px' }}>Type</th>
                <th style={{ padding: '12px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {records.length === 0 ? (
                <tr><td colSpan="5" style={{ padding: '30px', textAlign: 'center', color: '#888' }}>No records found for this month.</td></tr>
              ) : (
                records.map(rec => (
                  <tr key={rec.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '12px', fontSize: '13px' }}>{rec.date}</td>
                    <td style={{ padding: '12px', fontWeight:'500', color: '#172b4d' }}>{rec.employee_name}</td>
                    <td style={{ padding: '12px' }}>
                        <div style={{display:'flex', alignItems:'center', gap:'5px'}}>
                             <BiTime color="#6b778c"/> {rec.hours}
                        </div>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{ 
                        background: rec.type === 'Offday' ? '#FFFAE6' : '#E3FCEF',
                        color: rec.type === 'Offday' ? '#BF2600' : '#006644',
                        padding: '4px 8px', borderRadius: '4px', fontSize: '11px', fontWeight:'bold', textTransform: 'uppercase'
                      }}>
                        {rec.type}
                      </span>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <button onClick={() => handleDelete(rec.id)} style={{ color: '#de350b', background:'none', border:'none', cursor:'pointer' }}>
                        <BiTrash size={18} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

      </div>
    </div>
  );
};

const labelStyle = { display: 'block', fontSize: '12px', fontWeight: 'bold', marginBottom: '5px', color: '#5e6c84' };
const inputStyle = { width: '100%', padding: '10px', border: '1px solid #dfe1e6', borderRadius: '4px', fontSize: '14px', boxSizing: 'border-box', background: '#fafbfc' };

export default OvertimePage;