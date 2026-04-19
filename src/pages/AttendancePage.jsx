import React, { useState, useEffect } from 'react';
import ExcelJS from 'exceljs';
import { saveAs } from 'file-saver';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { employeeService, attendanceService } from '../services';
import { FiChevronLeft, FiChevronRight, FiXCircle, FiShieldOff, FiMoon, FiSun, FiCalendar, FiClock, FiDownload, FiFileText } from 'react-icons/fi';
import '../styles/AttendancePage.css';

// --- STYLES FOR EXCEL GRID ---
const excelStyles = {
    header: { font: { bold: true, color: { argb: 'FFFFFFFF' } }, fill: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF8E44AD' } }, alignment: { horizontal: 'center' }, border: { style: 'thin' } },
    m: { fill: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFFEB9C' } }, font: { color: { argb: 'FF9C6500' }, bold: true } },
    ni: { fill: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF2C3E50' } }, font: { color: { argb: 'FFFFFFFF' }, bold: true } },
    absent: { fill: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFFC7CE' } }, font: { color: { argb: 'FF9C0006' }, bold: true } },
    off: { fill: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFBDD7EE' } }, font: { color: { argb: 'FF1F4E78' }, bold: true } }
};

const formatDateLabel = (dateString) => {
    const date = new Date(dateString);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    return `${day}-${month}-${date.getFullYear()}`;
};

const AttendancePage = () => {
    const [employees, setEmployees] = useState([]);
    const [sortedEmployees, setSortedEmployees] = useState([]);
    const [attendance, setAttendance] = useState({});
    const [shifts, setShifts] = useState({});
    const [overtime, setOvertime] = useState({});
    const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
    const [isLoading, setIsLoading] = useState(true);
    const [message, setMessage] = useState(null);
    const [isDirty, setIsDirty] = useState(false);
    const [isExporting, setIsExporting] = useState(false);

    // 1. Load Data
    useEffect(() => {
        const load = async () => {
            try {
                setIsLoading(true);
                const [empData, attendData] = await Promise.all([employeeService.getAll(), attendanceService.getByDate(date)]);
                
                // Keep employees with valid IDs
                const mappedEmps = empData.map(e => ({ ...e, id: e.id || e.uid }));
                setEmployees(mappedEmps);

                const aMap = {}; const sMap = {}; const oMap = {};
                attendData.forEach(r => {
                    const id = r.employee_uid || r.employee_id;
                    aMap[id] = r.status;
                    sMap[id] = r.shift || 'Morning';
                    oMap[id] = r.overtime_hours || 0;
                });
                setAttendance(aMap); setShifts(sMap); setOvertime(oMap);
                setIsDirty(false);
            } catch (err) { console.error(err); }
            finally { setIsLoading(false); }
        };
        load();
    }, [date]);

    useEffect(() => {
        if (employees.length > 0) setSortedEmployees([...employees].sort((a, b) => a.id - b.id));
    }, [employees]);

    // 2. Handlers
    const handleToggle = (id) => {
        const current = attendance[id];
        const next = current === 'Present' ? 'Absent' : current === 'Absent' ? 'Off Day' : 'Present';
        setAttendance(prev => ({ ...prev, [id]: next }));
        if (next === 'Present' && !shifts[id]) setShifts(prev => ({ ...prev, [id]: 'Morning' }));
        setIsDirty(true);
    };

    const handleSubmit = async () => {
        setIsLoading(true);
        const records = Object.entries(attendance).filter(([_, s]) => s).map(([id, s]) => ({
            employee_id: parseInt(id), date, status: s,
            shift: s === 'Present' ? (shifts[id] || 'Morning') : "Morning",
            overtime_hours: s === 'Present' ? (parseInt(overtime[id]) || 0) : 0
        }));
        try {
            await attendanceService.updateBatch({ records });
            setMessage({ type: 'success', text: "Attendance Synced Successfully!" });
            setIsDirty(false);
        } catch (e) { setMessage({ type: 'error', text: "Sync Failed" }); }
        finally { setIsLoading(false); setTimeout(() => setMessage(null), 3000); }
    };

    // --- NEW: DAILY PDF HANDLER WITH ALERT ---
    const handleDailyPdfExport = async () => {
        setMessage({ type: 'success', text: "Generating Professional Daily PDF..." });
        try {
        await attendanceService.downloadPDF(date);
            setMessage({ type: 'success', text: "Daily PDF Downloaded!" });
        } catch (err) {
            setMessage({ type: 'error', text: "PDF Generation Failed" });
        } finally {
            setTimeout(() => setMessage(null), 4000);
        }
    };

    const handleMonthlyExcelExport = async () => {
        setIsExporting(true);
        setMessage({ type: 'success', text: "Generating Monthly Excel Grid..." });
        try {
            const d = new Date(date);
            const year = d.getFullYear();
            const month = d.getMonth() + 1;
            const monthlyData = await attendanceService.getByMonth(year, month);
            const attendanceMap = monthlyData.reduce((acc, r) => {
                const id = r.employee_uid || r.employee_id;
                const dayNum = new Date(r.date).getDate();
                if (!acc[id]) acc[id] = {};
                acc[id][dayNum] = r;
                return acc;
            }, {});

            const workbook = new ExcelJS.Workbook();
            const sheet = workbook.addWorksheet('Shift Tracker');
            sheet.addRow([`Monthly 12h Shift Tracker - ${d.toLocaleString('default', { month: 'long' })} ${year}`]);
            sheet.getRow(1).font = { bold: true, size: 14 };
            sheet.addRow([]);

            const headers = ['ID', 'Name', 'Designation'];
            for (let i = 1; i <= 31; i++) headers.push(i);
            headers.push('M', 'Ni', 'A', 'OT');
            const hRow = sheet.addRow(headers);
            hRow.eachCell(c => { c.style = excelStyles.header; });

            sortedEmployees.forEach(emp => {
                let counts = { m: 0, n: 0, a: 0, ot: 0 };
                const rowData = [emp.id, emp.name, emp.designation];
                for (let dNum = 1; dNum <= 31; dNum++) {
                    const r = attendanceMap[emp.id]?.[dNum];
                    let val = '';
                    if (r) {
                        if (r.status === 'Present') {
                            const char = r.shift === 'Night' ? 'Ni' : 'M';
                            val = r.overtime_hours > 0 ? `${char}+${r.overtime_hours}` : char;
                            r.shift === 'Night' ? counts.n++ : counts.m++;
                            counts.ot += r.overtime_hours;
                        } else if (r.status === 'Absent') { val = 'A'; counts.a++; }
                        else if (r.status === 'Off Day') { val = 'O'; }
                    }
                    rowData.push(val);
                }
                rowData.push(counts.m, counts.n, counts.a, counts.ot);
                const dRow = sheet.addRow(rowData);
                dRow.eachCell((cell, col) => {
                    cell.border = { top: {style:'thin'}, left: {style:'thin'}, bottom: {style:'thin'}, right: {style:'thin'} };
                    if (col > 3 && col <= 34) {
                        const v = String(cell.value);
                        if (v.includes('M')) cell.style = { ...cell.style, ...excelStyles.m };
                        if (v.includes('Ni')) cell.style = { ...cell.style, ...excelStyles.ni };
                        if (v === 'A') cell.style = { ...cell.style, ...excelStyles.absent };
                        if (v === 'O') cell.style = { ...cell.style, ...excelStyles.off };
                    }
                });
            });

            const buffer = await workbook.xlsx.writeBuffer();
            saveAs(new Blob([buffer]), `Shift_Tracker_${month}_${year}.xlsx`);
            setMessage({ type: 'success', text: "Excel Tracker Exported!" });
        } catch (e) { setMessage({ type: 'error', text: "Export Error" }); }
        finally { setIsExporting(false); setTimeout(() => setMessage(null), 3000); }
    };

    const CustomDateInput = React.forwardRef(({ onClick }, ref) => (
        <div className="custom-date-input" onClick={onClick} ref={ref}>
            <FiCalendar className="calendar-icon" />
            <span className="current-date">{formatDateLabel(date)}</span>
        </div>
    ));

    return (
        <div className="new-attendance-page">
            <div className="attendance-content-wrapper">
                {message && <div className={`message-toast ${message.type}`} style={{zIndex: 9999}}>{message.text}</div>}
                
                <div className="top-bar">
                    <div style={{display: 'flex', gap: '10px'}}>
                        <button className="top-bar-btn" onClick={handleMonthlyExcelExport} disabled={isExporting}>
                           <FiDownload /> {isExporting ? "..." : "Export Excel"}
                        </button>
                        {/* UPDATED BUTTON WITH ALERT HANDLER */}
                        <button className="top-bar-btn" onClick={handleDailyPdfExport}>
                            <FiFileText /> Export Daily PDF
                        </button>
                    </div>

                    <div className="date-navigator">
                        <FiChevronLeft className="date-arrow" onClick={() => {
                            const d = new Date(date); d.setDate(d.getDate() - 1); setDate(d.toISOString().split('T')[0]);
                        }} />
                        <DatePicker selected={new Date(date)} onChange={(d) => setDate(d.toISOString().split('T')[0])} customInput={<CustomDateInput />} />
                        <FiChevronRight className="date-arrow" onClick={() => {
                            const d = new Date(date); d.setDate(d.getDate() + 1); setDate(d.toISOString().split('T')[0]);
                        }} />
                    </div>

                    <button className="top-bar-btn-primary" onClick={handleSubmit} disabled={!isDirty || isLoading}>
                        {isLoading ? "Saving..." : "Confirm"}
                    </button>
                </div>

                <div className="controls-and-legend">
                    <div className="sort-control">
                        <label>Mark All:</label>
                        <select onChange={(e) => {
                            const s = e.target.value; const newA = {};
                            sortedEmployees.forEach(emp => newA[emp.id] = s);
                            setAttendance(newA); setIsDirty(true);
                        }} value="">
                            <option value="" disabled>Select...</option>
                            <option value="Present">Present</option>
                            <option value="Absent">Absent</option>
                            <option value="Off Day">Off Day</option>
                        </select>
                    </div>
                    <div className="legend">
                        <div className="legend-item"><span className="color-box present-mrng"></span>Morning</div>
                        <div className="legend-item"><span className="color-box present-night"></span>Night</div>
                        <div className="legend-item"><span className="color-box absent"></span>Absent</div>
                    </div>
                </div>

                <div className="class-summary">
                    {Object.values(attendance).filter(s => s === 'Present').length} / {employees.length} Present
                </div>

                <div className="employee-grid">
                    {sortedEmployees.map(emp => {
                        const s = attendance[emp.id];
                        const shift = shifts[emp.id] || 'Morning';
                        let cardClass = s === 'Absent' ? 'absent' : s === 'Off Day' ? 'off-day' : s === 'Present' ? (shift === 'Night' ? 'present-night' : 'present-mrng') : 'unmarked';

                        return (
                            <div key={emp.id} className={`employee-card ${cardClass}`} onClick={() => handleToggle(emp.id)}>
                                <div className="employee-card-info">
                                    <span className="employee-card-name">{emp.name}</span>
                                    <span className="employee-card-id">ID: {String(emp.id).padStart(2, '0')}</span>
                                    {s === 'Present' && (
                                        <div className="card-controls" onClick={e => e.stopPropagation()}>
                                            <select className="card-shift-select" value={shift} onChange={e => {setShifts({...shifts, [emp.id]: e.target.value}); setIsDirty(true)}}>
                                                <option value="Morning">Morning (12h)</option>
                                                <option value="Night">Night (12h)</option>
                                            </select>
                                            <div className="ot-input-wrapper">
                                                <FiClock className="ot-icon" />
                                                <input type="number" className="card-ot-input" value={overtime[emp.id] || ''} onChange={e => {setOvertime({...overtime, [emp.id]: e.target.value}); setIsDirty(true)}} />
                                            </div>
                                        </div>
                                    )}
                                    {s !== 'Present' && <span className="employee-card-reg">{emp.designation}</span>}
                                </div>
                                <div className="status-icon">
                                    {s === 'Present' && (shift === 'Night' ? <FiMoon /> : <FiSun />)}
                                    {s === 'Absent' && <FiXCircle />}
                                    {s === 'Off Day' && <FiShieldOff />}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default AttendancePage;