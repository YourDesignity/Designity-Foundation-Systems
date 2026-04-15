import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  BiSearch, BiCalculator, BiDownload, BiErrorCircle, BiCheckCircle, BiLoaderAlt, BiCheck, BiTimeFive 
} from 'react-icons/bi';
// Ensure this path matches your project structure
import { getEmployees } from '../services/apiService'; 
import '../styles/projectsPage.css'; // Or your relevant CSS file

const PayslipsPage = () => {
  // --- STATE ---
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  
  const [dbEmployees, setDbEmployees] = useState([]); 
  const [tableData, setTableData] = useState([]);     
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  
  const [modal, setModal] = useState({ show: false, type: '', title: '', message: '' });
  const [downloadingId, setDownloadingId] = useState(null); 
  const [downloadedIds, setDownloadedIds] = useState([]); 

  // --- HELPER: AUTH HEADERS ---
  const getAuthHeaders = () => {
    let token = localStorage.getItem('access_token') || localStorage.getItem('token');
    
    if (token && token.startsWith('"') && token.endsWith('"')) {
      token = token.slice(1, -1);
    }
    
    if (!token) return null;
    return { 
      headers: { 
        'Authorization': `Bearer ${token}`, 
        'Content-Type': 'application/json' 
      } 
    };
  };

  // --- 1. LOAD EMPLOYEES ---
  useEffect(() => {
    const fetchEmployees = async () => {
      try {
        setLoading(true);
        const data = await getEmployees();
        if (Array.isArray(data)) {
          setDbEmployees(data);
          // Initialize table structure with default values
          setTableData(data.map(emp => ({
            employee_id: emp.id || emp.uid, 
            name: emp.name,
            designation: emp.designation,
            gross_salary: 0, 
            total_deductions: 0, 
            net_salary: 0, 
            days_present: 0,
            overtime_hours: 0, 
            overtime_salary: 0, 
            standard_work_days: emp.standard_work_days || 26,
            isCalculated: false 
          })));
        }
      } catch (error) { 
        console.error("Failed to load employees"); 
      } finally { 
        setLoading(false); 
      }
    };
    fetchEmployees();
  }, []);

  // --- 2. CALCULATE PAYSLIPS (Batch) ---
  const handleCalculate = async () => {
    if (dbEmployees.length === 0) return showAlert('error', 'No Data', "No employees found.");
    
    const config = getAuthHeaders();
    if (!config) return showAlert('error', 'Auth Error', "Please login again.");

    setLoading(true);
    setDownloadedIds([]); 
    
    const employeeIds = dbEmployees.map(emp => emp.id || emp.uid);

    try {
      const response = await axios.post(
        'http://localhost:8000/payslips/calculate', 
        { employee_ids: employeeIds, pay_period: selectedMonth },
        config 
      );

      if (response.data.status === 'success') {
        const results = response.data.payslips_data;
        
        // Merge Backend Results into Table Data
        setTableData(prev => prev.map(row => {
          const res = results.find(r => r.employee_id === row.employee_id);
          if (res) {
            return { 
                ...row, 
                ...res, 
                isCalculated: true 
            }; 
          }
          return row; 
        }));
        showAlert('success', 'Calculation Complete', `Processed ${results.length} payslips.`);
      }
    } catch (error) {
      console.error("Calculation error:", error);
      showAlert('error', 'Calculation Failed', "Could not calculate salaries. Check backend logs.");
    } finally {
      setLoading(false);
    }
  };

  // --- 3. DOWNLOAD PDF ---
  const handleDownloadPDF = async (employeeId, employeeName) => {
    const config = getAuthHeaders();
    if (!config) return showAlert('error', 'Auth Error', "Please login.");

    setDownloadingId(employeeId);

    try {
      const response = await axios.get(
        `http://localhost:8000/payslips/download/${employeeId}`, 
        { ...config, params: { month: selectedMonth }, responseType: 'blob' }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Payslip_${employeeName}_${selectedMonth}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setDownloadedIds(prev => [...prev, employeeId]);
      showAlert('success', 'Download Successful', `Payslip for ${employeeName} saved.`);

    } catch (error) {
      if (error.response && error.response.data instanceof Blob) {
         const reader = new FileReader();
         reader.onload = () => {
             try { 
               const errJson = JSON.parse(reader.result);
               showAlert('error', 'Download Failed', errJson.detail || "Server error");
             } catch (e) { 
               showAlert('error', 'Server Error', "Check backend logs."); 
             }
         }
         reader.readAsText(error.response.data);
      } else {
        showAlert('error', 'Download Failed', "Network error or server offline.");
      }
    } finally {
        setDownloadingId(null);
    }
  };

  // --- UI HELPERS ---
  const showAlert = (type, title, message) => {
    setModal({ show: true, type, title, message });
  };
  const closeModal = () => setModal({ show: false, type: '', title: '', message: '' });

  const filteredData = tableData.filter(p => {
    const term = searchTerm.toLowerCase();
    const nameMatch = p.name.toLowerCase().includes(term);
    const idMatch = String(p.employee_id).includes(term);
    return nameMatch || idMatch;
  });

  return (
    <div className="projects-container" style={{ padding: '20px', background: '#f4f5f7', minHeight: '100vh' }}>
      
      {/* HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ margin: 0, color: '#172b4d' }}>Payslips</h2>
          <p style={{ margin: 0, color: '#6b778c', fontSize: '14px' }}>Pages / Payslips</p>
        </div>
        <div style={{ position: 'relative' }}>
          <BiSearch style={{ position: 'absolute', left: '10px', top: '10px', color: '#aaa' }} />
          <input 
            type="text" placeholder="Search by Name or ID..." value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ padding: '8px 8px 8px 35px', borderRadius: '4px', border: '1px solid #ddd', width: '250px' }}
          />
        </div>
      </div>

      {/* CONTROL PANEL */}
      <div style={{ background: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '15px' }}>
            <div style={{ fontSize: '30px', color: '#4c35de' }}><BiCalculator /></div>
            <div>
              <h3 style={{ margin: 0, fontSize: '18px' }}>Payslip Generation</h3>
              <p style={{ margin: '5px 0 0', color: '#6b778c', fontSize: '13px' }}>
                Found {dbEmployees.length} active employees in database.
              </p>
            </div>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', marginBottom: '5px', color: '#5e6c84' }}>Select Pay Period:</label>
            <div style={{ display: 'flex', alignItems: 'center', border: '1px solid #dfe1e6', padding: '5px 10px', borderRadius: '4px', background: '#fafbfc' }}>
              <input 
                type="month" value={selectedMonth} onChange={(e) => setSelectedMonth(e.target.value)}
                style={{ border: 'none', outline: 'none', background: 'transparent', fontSize: '14px', color: '#172b4d', fontWeight: 500 }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ACTION BAR */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginBottom: '15px' }}>
        <button 
          onClick={handleCalculate} disabled={loading}
          style={{ 
            background: '#4c35de', color: 'white', border: 'none', padding: '10px 20px', 
            borderRadius: '6px', cursor: loading ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
            opacity: loading ? 0.7 : 1, transition: 'background 0.2s', fontWeight: '500'
          }}
        >
          {loading ? <><BiLoaderAlt className="spin-icon" /> Calculating...</> : <><BiCalculator /> Calculate & Preview</>}
        </button>
      </div>

      {/* TABLE */}
      <div style={{ background: 'white', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f4f5f7', borderBottom: '2px solid #eee', textAlign: 'left', color: '#5e6c84', fontSize: '12px', textTransform: 'uppercase' }}>
              <th style={{ padding: '15px' }}>Employee</th>
              <th style={{ padding: '15px' }}>Days Worked</th>
              <th style={{ padding: '15px' }}>OT (Hrs)</th>
              <th style={{ padding: '15px' }}>Earnings</th>
              <th style={{ padding: '15px' }}>Deductions</th>
              <th style={{ padding: '15px' }}>Net Pay</th>
              <th style={{ padding: '15px', textAlign: 'center' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredData.length === 0 ? (
              <tr><td colSpan="7" style={{ padding: '40px', textAlign: 'center', color: '#888' }}>{loading ? 'Loading...' : 'No matching employees found.'}</td></tr>
            ) : (
              filteredData.map((slip) => {
                const isDownloading = downloadingId === slip.employee_id;
                const isDownloaded = downloadedIds.includes(slip.employee_id);
                // Check if OT exists for styling
                const hasOT = slip.overtime_hours && slip.overtime_hours > 0;

                return (
                  <tr key={slip.employee_id} style={{ borderBottom: '1px solid #eee', transition: 'background 0.1s' }}>
                    <td style={{ padding: '15px' }}>
                      <div style={{ fontWeight: 'bold', color: '#172b4d' }}>{slip.name}</div>
                      <div style={{ fontSize: '12px', color: '#6b778c' }}>{slip.designation || 'Staff'} <span style={{color:'#ccc'}}>|</span> ID: {slip.employee_id}</div>
                    </td>
                    
                    {/* DAYS WORKED */}
                    <td style={{ padding: '15px' }}>
                        {slip.isCalculated ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontWeight: '500', color: '#172b4d' }}>
                                <BiTimeFive style={{ color: '#6b778c' }}/>
                                {slip.days_present} <span style={{ color: '#aaa', fontSize: '12px' }}>/ {slip.standard_work_days}</span>
                            </div>
                        ) : (
                            <span style={{ color: '#aaa' }}>-</span>
                        )}
                    </td>

                    {/* OT COLUMN (Updated: Removed Background Color) */}
                    <td style={{ padding: '15px' }}>
                       {slip.isCalculated ? (
                           hasOT ? (
                               <div>
                                   <div style={{ fontWeight: 'bold', color: '#B76E00' }}>{slip.overtime_hours} Hrs</div>
                                   <div style={{ fontSize: '11px', color: '#6b778c' }}>+{slip.overtime_salary} KWD</div>
                               </div>
                           ) : <span style={{ color: '#aaa' }}>-</span>
                       ) : <span style={{ color: '#aaa' }}>-</span>}
                    </td>

                    {/* EARNINGS */}
                    <td style={{ padding: '15px', color: slip.isCalculated ? '#006644' : '#aaa', fontWeight: slip.isCalculated ? '500' : 'normal' }}>
                      {slip.isCalculated ? `${slip.gross_salary} KWD` : '-'}
                    </td>

                    {/* DEDUCTIONS */}
                    <td style={{ padding: '15px', color: slip.isCalculated ? '#de350b' : '#aaa' }}>
                      {slip.isCalculated ? slip.total_deductions : '-'}
                    </td>

                    {/* NET PAY */}
                    <td style={{ padding: '15px', fontWeight: 'bold', color: slip.isCalculated ? '#172b4d' : '#aaa', fontSize: '15px' }}>
                      {slip.isCalculated ? `${slip.net_salary} KWD` : 'Wait'}
                    </td>

                    {/* ACTION */}
                    <td style={{ padding: '15px', textAlign: 'center' }}>
                      <button 
                        onClick={() => handleDownloadPDF(slip.employee_id, slip.name)}
                        disabled={!slip.isCalculated || isDownloading}
                        style={{ 
                          background: isDownloaded ? '#e3fcef' : (isDownloading ? '#deebff' : '#ebecf0'),
                          color: isDownloaded ? '#006644' : (isDownloading ? '#0052cc' : '#42526e'),
                          border: 'none',
                          padding: '6px 12px', borderRadius: '4px', 
                          cursor: slip.isCalculated ? 'pointer' : 'not-allowed', 
                          display: 'inline-flex', alignItems: 'center', gap: '5px', 
                          fontWeight: '500', fontSize: '13px',
                          minWidth: '100px', justifyContent: 'center'
                        }}
                      >
                        {isDownloading ? <><BiLoaderAlt className="spin-icon" /> Sending...</> : isDownloaded ? <><BiCheck /> Done</> : <><BiDownload /> PDF</>}
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* MODAL COMPONENT */}
      {modal.show && (
        <div style={{ 
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
          background: 'rgba(9, 30, 66, 0.54)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 
        }}>
          <div style={{ background: 'white', padding: '25px', borderRadius: '8px', textAlign: 'left', width: '400px', boxShadow: '0 8px 30px rgba(0,0,0,0.12)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
              <div style={{ color: modal.type === 'error' ? '#de350b' : '#006644', fontSize: '24px', display: 'flex' }}>
                {modal.type === 'error' ? <BiErrorCircle /> : <BiCheckCircle />}
              </div>
              <h3 style={{ margin: 0, fontSize: '18px', color: '#172b4d' }}>{modal.title}</h3>
            </div>
            <p style={{ color: '#6b778c', fontSize: '14px', margin: '0 0 20px 34px', lineHeight: '1.5' }}>{modal.message}</p>
            <div style={{ textAlign: 'right' }}>
              <button 
                onClick={closeModal}
                style={{ background: modal.type === 'error' ? '#de350b' : '#006644', color: 'white', border: 'none', padding: '8px 24px', borderRadius: '4px', cursor: 'pointer', fontWeight: '500', fontSize: '14px' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .spin-icon { animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default PayslipsPage;