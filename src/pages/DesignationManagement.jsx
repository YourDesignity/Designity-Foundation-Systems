import React, { useState, useEffect } from 'react';
import Select from 'react-select'; 
import { getDesignations, addDesignation, deleteDesignation, getEmployees, updateEmployee } from '../services/apiService'; 
import '../styles/siteManagement.css'; 
import { FaUserTag, FaTrash, FaPlus, FaBriefcase, FaInfoCircle, FaUsers } from 'react-icons/fa';

// 1. Import SweetAlert2
import Swal from 'sweetalert2';

const DesignationManagement = () => {
    const [designations, setDesignations] = useState([]);
    const [allEmployees, setAllEmployees] = useState([]); 
    const [employeeCounts, setEmployeeCounts] = useState({});
    
    // Form State
    const [newRole, setNewRole] = useState('');
    const [selectedOptions, setSelectedOptions] = useState([]); 
    
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [desData, empData] = await Promise.all([
                getDesignations(),
                getEmployees()
            ]);

            setDesignations(desData);
            
            const formattedEmployees = Array.isArray(empData) ? empData.map(emp => ({
                value: emp.id,
                label: `${emp.name} — ${emp.designation || 'No Role'}`
            })) : [];
            
            setAllEmployees(formattedEmployees);

            const counts = {};
            if (Array.isArray(empData)) {
                empData.forEach(emp => {
                    if (emp.designation) {
                        counts[emp.designation] = (counts[emp.designation] || 0) + 1;
                    }
                });
            }
            setEmployeeCounts(counts);

        } catch (err) {
            console.error(err);
            setError('Could not load data.');
        } finally {
            setLoading(false);
        }
    };

    const handleSelectChange = (selected) => {
        setSelectedOptions(selected || []);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!newRole.trim()) return;

        setIsSubmitting(true);
        setError('');

        try {
            // Step 1: Create the Designation
            await addDesignation(newRole);

            // Step 2: Update selected employees
            if (selectedOptions.length > 0) {
                const updatePromises = selectedOptions.map(option => {
                    return updateEmployee(option.value, { designation: newRole });
                });
                await Promise.all(updatePromises);
            }

            // Step 3: Reset and Refresh
            setNewRole('');
            setSelectedOptions([]);
            await fetchData(); 
            
            // --- UPDATED SUCCESS POPUP ---
            await Swal.fire({
                title: 'Success!',
                text: 'Designation created and employees assigned successfully!',
                icon: 'success',
                confirmButtonText: 'Done',
                confirmButtonColor: '#4f46e5', // Matches your Indigo theme
                timer: 3000,
                timerProgressBar: true
            });

        } catch (err) {
            console.error(err);
            // Error Popup
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: err.message || "Failed to process request",
            });
            setError(err.message || "Failed to process request");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleDelete = async (id) => {
        // --- UPDATED DELETE CONFIRMATION ---
        const result = await Swal.fire({
            title: 'Are you sure?',
            text: "You won't be able to revert this!",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            cancelButtonColor: '#3085d6',
            confirmButtonText: 'Yes, delete it!'
        });

        if (result.isConfirmed) {
            try {
                await deleteDesignation(id);
                setDesignations(prev => prev.filter(d => (d.id || d._id) !== id));
                
                // Success feedback after delete
                Swal.fire(
                    'Deleted!',
                    'The designation has been deleted.',
                    'success'
                );
            } catch (err) {
                Swal.fire('Error', "Failed to delete: " + err.message, 'error');
            }
        }
    };

    // --- CUSTOM STYLES FOR REACT SELECT ---
    const customSelectStyles = {
        control: (provided, state) => ({
            ...provided,
            padding: '5px',
            borderColor: state.isFocused ? '#4f46e5' : '#ddd',
            boxShadow: state.isFocused ? '0 0 0 2px rgba(79, 70, 229, 0.2)' : 'none',
            borderRadius: '8px',
            minHeight: '45px', 
            '&:hover': { borderColor: '#4f46e5' }
        }),
        multiValue: (provided) => ({
            ...provided,
            backgroundColor: '#e0e7ff', 
            borderRadius: '4px',
        }),
        multiValueLabel: (provided) => ({
            ...provided,
            color: '#3730a3', 
            fontWeight: '500',
        }),
        multiValueRemove: (provided) => ({
            ...provided,
            color: '#3730a3',
            ':hover': {
                backgroundColor: '#4f46e5',
                color: 'white',
            },
        }),
        menu: (provided) => ({
            ...provided,
            borderRadius: '8px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
            zIndex: 9999 
        }),
    };

    return (
        <div className="site-page-container">
            <div className="page-header">
                <h2><FaUserTag className="header-icon" /> Designation Management</h2>
                <p>Create and manage employee job titles and roles.</p>
            </div>

            <div className="site-content-wrapper">
                {/* --- LEFT: ADD NEW ROLE FORM --- */}
                <div className="site-form-section" style={{ height: 'fit-content' }}>
                    <div className="form-header">
                        <h3><FaPlus /> Add New Role</h3>
                    </div>
                    
                    {error && <div className="error-banner">{error}</div>}

                    <form onSubmit={handleSubmit} className="modern-form">
                        
                        <div className="form-group">
                            <label>Designation Title</label>
                            <input 
                                type="text" 
                                value={newRole}
                                onChange={(e) => setNewRole(e.target.value)}
                                placeholder="e.g. Senior Accountant" 
                                required
                                style={{ padding: '12px', borderRadius: '8px', border: '1px solid #ddd' }}
                            />
                        </div>

                        <div className="form-group" style={{ marginBottom: '20px' }}>
                            <label style={{ marginBottom: '8px', display: 'block' }}>Assign Employees</label>
                            
                            <Select 
                                isMulti
                                options={allEmployees}
                                value={selectedOptions}
                                onChange={handleSelectChange}
                                placeholder="Select employees to assign..."
                                styles={customSelectStyles}
                                closeMenuOnSelect={false} 
                            />
                        </div>

                        <button type="submit" className="save-btn" disabled={isSubmitting} style={{ padding: '12px', fontSize: '1rem' }}>
                            {isSubmitting ? 'Processing...' : 'Add Designation & Assign'}
                        </button>
                    </form>
                    
                    <div style={{ marginTop: '20px', fontSize: '0.85rem', color: '#6b7280', display: 'flex', gap: '8px', lineHeight: '1.4' }}>
                        <FaInfoCircle style={{ flexShrink: 0, marginTop: '3px' }} />
                        <p style={{ margin: 0 }}>
                            Employees selected above will be instantly moved to this new designation. 
                            You can search by typing in the box.
                        </p>
                    </div>
                </div>

                {/* --- RIGHT: LIST OF ROLES --- */}
                <div className="site-list-section">
                    <div className="list-header">
                        <h3>Existing Roles <span className="count-badge">{designations.length}</span></h3>
                    </div>

                    {loading ? (
                        <div className="loading-state">Loading roles...</div>
                    ) : (
                        <div className="site-grid">
                            {designations.length === 0 ? (
                                <div className="empty-state">
                                    <FaUserTag className="empty-icon" />
                                    <p>No designations added yet.</p>
                                </div>
                            ) : (
                                designations.map((role) => (
                                    <div key={role.id || role._id} className="site-card" style={{ minHeight: 'auto' }}>
                                        <div className="site-card-top">
                                            <div className="site-info">
                                                <h4 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '10px', margin: 0 }}>
                                                    <FaBriefcase style={{ color: '#4f46e5' }}/> 
                                                    {role.title || role.name}
                                                </h4>
                                                
                                                <div style={{ fontSize: '0.9rem', color: '#666', marginTop: '5px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                    <FaUsers size={14} />
                                                    {employeeCounts[role.title || role.name] || 0} Employees
                                                </div>
                                            </div>
                                            <button 
                                                className="delete-icon-btn" 
                                                onClick={() => handleDelete(role.id || role._id)}
                                                title="Delete Role"
                                            >
                                                <FaTrash />
                                            </button>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default DesignationManagement;