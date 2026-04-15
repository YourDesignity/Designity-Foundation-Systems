import React, { useState, useEffect } from 'react';
import { getSites, addSite, deleteSite } from '../services/apiService'; 
import '../styles/siteManagement.css';
import { FaTrash, FaMapMarkerAlt, FaPhone, FaBuilding, FaPlusCircle, FaUserTie } from 'react-icons/fa';

// --- HARDCODED MANAGER LIST ---
const AVAILABLE_MANAGERS = [
    "Manager 1",
    "Manager 2",
    "Manager 3",
    "Site Supervisor A",
    "Site Supervisor B"
];

const SiteManagement = () => {
    const [sites, setSites] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
        
    const [formData, setFormData] = useState({
        name: '', 
        location: '',
        company_details: '', 
        contact_number: '',
        manager: '' 
    });

    useEffect(() => {
        fetchSites();
    }, []);

    const fetchSites = async () => {
        try {
            const data = await getSites();
            // DEBUG: This logs the "Dummy" card structure. Check Console (F12) to see correct field names.
            if (data.length > 0) {
                console.log("Correct Field Structure (from DB):", data[0]); 
            }
            setSites(data);
        } catch (err) {
            setError('Failed to load sites.');
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    // --- FIXED SUBMIT: Sends data with multiple common field names ---
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        
        // We create a "Smart Payload" that includes variations of field names.
        // This ensures the backend finds the data whether it expects 'manager' or 'site_manager', etc.
        const smartPayload = {
            name: formData.name,
            location: formData.location,
            
            // Send Manager as both 'manager' and 'site_manager'
            manager: formData.manager,
            site_manager: formData.manager, 
            
            // Send Details as 'company_details', 'description', and 'details'
            company_details: formData.company_details,
            description: formData.company_details,
            details: formData.company_details,
            
            // Send Phone as 'contact_number', 'phone', and 'mobile'
            contact_number: formData.contact_number,
            phone: formData.contact_number,
            mobile: formData.contact_number
        };

        try {
            console.log("Sending Smart Payload:", smartPayload); 
            await addSite(smartPayload);
            
            await fetchSites(); // Refresh list to get new data
            setFormData({ name: '', location: '', company_details: '', contact_number: '', manager: '' });
            alert("Site created successfully!");
            
        } catch (err) {
            console.error("Creation Error:", err);
            if (err.message && err.message.includes("UNIQUE")) {
                setError(`The site name "${formData.name}" is already taken.`);
            } else {
                setError(err.message || 'Failed to add site');
            }
        }
    };

    // --- HELPER: Get ID safely ---
    const getSiteId = (site) => {
        return site.id || site._id || site.site_id || site.ID;
    };

    const handleDelete = async (site) => {
        const id = getSiteId(site);
        if (!id) return alert("Error: Site ID missing.");

        if(!window.confirm(`Delete "${site.name}"?`)) return;
        
        try {
            await deleteSite(id);
            setSites(prevSites => prevSites.filter(s => getSiteId(s) !== id));
        } catch (err) {
            if (err.message.includes("Not Found") || err.message.includes("404")) {
                setSites(prevSites => prevSites.filter(s => getSiteId(s) !== id));
            } else {
                alert(`Failed to delete: ${err.message}`);
            }
        }
    }

    return (
        <div className="site-page-container">
            <div className="page-header">
                <h2><FaBuilding className="header-icon" /> Site Management</h2>
                <p>Manage work locations and assign site managers</p>
            </div>

            <div className="site-content-wrapper">
                {/* --- LEFT PANEL: FORM --- */}
                <div className="site-form-section">
                    <div className="form-header">
                        <h3><FaPlusCircle /> Add New Site</h3>
                    </div>
                    
                    {error && <div className="error-banner">{error}</div>}
                    
                    <form onSubmit={handleSubmit} className="modern-form">
                        <div className="form-group">
                            <label>Site Name</label>
                            <input 
                                type="text" name="name" required 
                                value={formData.name} onChange={handleChange} 
                                placeholder="e.g. Main Headquarters" 
                            />
                        </div>

                        <div className="form-group">
                            <label>Assign Manager</label>
                            <select 
                                name="manager" 
                                value={formData.manager} 
                                onChange={handleChange}
                                required
                                className="manager-select"
                            >
                                <option value="">-- Select a Manager --</option>
                                {AVAILABLE_MANAGERS.map((mgr, index) => (
                                    <option key={index} value={mgr}>{mgr}</option>
                                ))}
                            </select>
                        </div>

                        <div className="form-group">
                            <label>Location / Address</label>
                            <input 
                                type="text" name="location" required 
                                value={formData.location} onChange={handleChange} 
                                placeholder="e.g. 123 Business Rd" 
                            />
                        </div>
                        <div className="form-group">
                            <label>Company Details</label>
                            <textarea 
                                name="company_details" 
                                value={formData.company_details} onChange={handleChange} 
                                placeholder="Project description..." 
                            />
                        </div>
                        <div className="form-group">
                            <label>Contact Number</label>
                            <input 
                                type="text" name="contact_number" 
                                value={formData.contact_number} onChange={handleChange} 
                                placeholder="+1 (555) 000-0000" 
                            />
                        </div>
                        <button type="submit" className="save-btn">Create Site</button>
                    </form>
                </div>

                {/* --- RIGHT PANEL: LIST --- */}
                <div className="site-list-section">
                    <div className="list-header">
                        <h3>Existing Sites <span className="count-badge">{sites.length}</span></h3>
                    </div>

                    {loading ? (
                        <div className="loading-state">Loading sites...</div>
                    ) : (
                        <div className="site-grid">
                            {sites.length === 0 ? (
                                <div className="empty-state">
                                    <FaBuilding className="empty-icon" />
                                    <p>No sites added yet.</p>
                                </div>
                            ) : (
                                sites.map(site => {
                                    const siteId = getSiteId(site);
                                    
                                    // --- RENDER LOGIC: Check all possible field names ---
                                    const managerName = site.manager || site.site_manager || site.assigned_to || "Unassigned";
                                    const detailsText = site.company_details || site.companyDetails || site.description || site.details || "No details provided.";
                                    const contactText = site.contact_number || site.contactNumber || site.phone || site.mobile;

                                    return (
                                        <div key={siteId || Math.random()} className="site-card">
                                            <div className="site-card-top">
                                                <div className="site-info">
                                                    <h4>{site.name}</h4>
                                                    <span className="location-tag">
                                                        <FaMapMarkerAlt /> {site.location}
                                                    </span>
                                                </div>
                                                <button 
                                                    className="delete-icon-btn" 
                                                    onClick={() => handleDelete(site)}
                                                >
                                                    <FaTrash />
                                                </button>
                                            </div>
                                            
                                            <div className="site-card-body">
                                                <div className="manager-display">
                                                    <FaUserTie className="manager-icon" />
                                                    <span>{managerName}</span>
                                                </div>
                                                <p className="site-desc">{detailsText}</p>
                                            </div>

                                            <div className="site-card-footer">
                                                {contactText ? (
                                                    <span className="contact-info"><FaPhone /> {contactText}</span>
                                                ) : (
                                                    <span className="contact-info text-muted">No contact info</span>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SiteManagement;