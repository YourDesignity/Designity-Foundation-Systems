import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BiMinusCircle, BiTrash } from 'react-icons/bi';
import { getEmployees } from '../services/apiService'; 
import '../styles/projectsPage.css';

const DeductionsPage = () => {
  const [employees, setEmployees] = useState([]);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });

  const [formData, setFormData] = useState({
    employee_id: '',
    pay_period: '', 
    amount: '',
    reason: ''
  });

  // Init Form pay_period when month changes
  useEffect(() => {
    setFormData(prev => ({ ...prev, pay_period: selectedMonth }));
  }, [selectedMonth]);

  const getAuthHeaders = () => {
    let token = localStorage.getItem('access_token') || localStorage.getItem('token');
    if (token && token.startsWith('"')) token = token.slice(1, -1);
    return { headers: { 'Authorization': `Bearer ${token}` } };
  };

  useEffect(() => {
    fetchEmployees();
  }, []);

  useEffect(() => {
    fetchDeductions();
  }, [selectedMonth]);

  const fetchEmployees = async () => {
    try {
      const data = await getEmployees();
      setEmployees(data);
    } catch (err) { console.error("Error loading employees"); }
  };

  const fetchDeductions = async () => {
    const [year, month] = selectedMonth.split('-');
    try {
      const res = await axios.get(`http://localhost:8000/deductions/${year}/${month}`, getAuthHeaders());
      setRecords(res.data);
    } catch (err) { console.error("Error loading deductions"); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if(!formData.employee_id || !formData.amount) return alert("Please fill details");
    
    setLoading(true);
    
    // Convert types for Backend
    const payload = {
        ...formData,
        employee_id: parseInt(formData.employee_id),
        amount: parseFloat(formData.amount)
    };

    try {
      await axios.post('http://localhost:8000/deductions/', payload, getAuthHeaders());
      
      setFormData({ ...formData, amount: '', reason: '' }); 
      fetchDeductions();
      alert("Deduction Applied Successfully");
    } catch (error) {
      console.error(error);
      alert("Failed to add deduction. Check console.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this deduction?")) return;
    try {
      await axios.delete(`http://localhost:8000/deductions/${id}`, getAuthHeaders());
      fetchDeductions();
    } catch (err) { alert("Delete failed"); }
  };

  return (
    <div style={{ padding: '20px', background: '#f4f5f7', minHeight: '100vh' }}>
      
      {/* HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
            <h2 style={{ margin: 0, color: '#172b4d' }}>Deductions & Penalties</h2>
            <p style={{ margin: 0, color: '#6b778c', fontSize: '14px' }}>Salary advances, fines, and asset damages</p>
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
          <h3 style={{ marginTop: 0, color: '#de350b', display:'flex', alignItems:'center', gap:'10px' }}><BiMinusCircle /> Add Deduction</h3>
          
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

            <div>
              <label style={labelStyle}>Pay Period</label>
              <input 
                type="month" style={inputStyle} value={formData.pay_period}
                onChange={(e) => setFormData({...formData, pay_period: e.target.value})}
                required
                disabled // Lock to the top selector
              />
            </div>

            <div>
              <label style={labelStyle}>Amount (KWD)</label>
              <input 
                type="number" step="0.01" min="0.1" style={inputStyle} value={formData.amount}
                onChange={(e) => setFormData({...formData, amount: e.target.value})}
                placeholder="e.g. 25.000" required
              />
            </div>

            <div>
              <label style={labelStyle}>Reason</label>
              <input 
                type="text" style={inputStyle} value={formData.reason}
                onChange={(e) => setFormData({...formData, reason: e.target.value})}
                placeholder="e.g. Uniform Lost" required
              />
            </div>

            <button 
              type="submit" disabled={loading}
              style={{ background: '#de350b', color: 'white', padding: '12px', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight:'bold', marginTop:'10px' }}
            >
              {loading ? 'Processing...' : 'Apply Deduction'}
            </button>
          </form>
        </div>

        {/* RIGHT: TABLE */}
        <div style={{ flex: '2 1 500px', background: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' }}>
          <h3 style={{ marginTop: 0, marginBottom:'15px', color: '#172b4d' }}>Deductions for {selectedMonth}</h3>
          
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f4f5f7', textAlign: 'left', color: '#5e6c84', fontSize:'13px', textTransform:'uppercase' }}>
                <th style={{ padding: '12px' }}>Period</th>
                <th style={{ padding: '12px' }}>Employee</th>
                <th style={{ padding: '12px' }}>Amount</th>
                <th style={{ padding: '12px' }}>Reason</th>
                <th style={{ padding: '12px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {records.length === 0 ? (
                <tr><td colSpan="5" style={{ padding: '30px', textAlign: 'center', color: '#888' }}>No deductions found.</td></tr>
              ) : (
                records.map(rec => (
                  <tr key={rec.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '12px', fontSize:'13px', color:'#777' }}>{rec.date || selectedMonth}</td>
                    <td style={{ padding: '12px', fontWeight:'500', color:'#172b4d' }}>{rec.employee_name}</td>
                    <td style={{ padding: '12px', color: '#de350b', fontWeight:'bold' }}>-{rec.amount} KWD</td>
                    <td style={{ padding: '12px', color: '#42526e' }}>{rec.reason}</td>
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

export default DeductionsPage;