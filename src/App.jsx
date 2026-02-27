import React, { useState, useMemo } from 'react'
import './App.css'

function App() {
    const [invoices, setInvoices] = useState([])
    const [processing, setProcessing] = useState(false)
    const [isDragging, setIsDragging] = useState(false)

    // Memoized stats for the dashboard
    const stats = useMemo(() => {
        const done = invoices.filter(inv => inv.status === 'done')
        return {
            total: invoices.length,
            processed: done.length,
            pending: invoices.filter(inv => inv.status === 'pending').length,
            totalAmount: done.reduce((sum, inv) => sum + (inv.data?.total_amount || 0), 0)
        }
    }, [invoices])

    const handleFiles = (files) => {
        const newItems = files.map(f => ({
            file: f,
            status: 'pending',
            id: Math.random().toString(36).substr(2, 9),
            data: null,
            error: null
        }))
        setInvoices(prev => [...prev, ...newItems])
    }

    const handleFileUpload = (e) => {
        handleFiles(Array.from(e.target.files))
    }

    const onDragOver = (e) => {
        e.preventDefault()
        setIsDragging(true)
    }

    const onDragLeave = () => {
        setIsDragging(false)
    }

    const onDrop = (e) => {
        e.preventDefault()
        setIsDragging(false)
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFiles(Array.from(e.dataTransfer.files))
            e.dataTransfer.clearData()
        }
    }

    const processAll = async () => {
        const pendingInvoices = invoices.filter(inv => inv.status === 'pending')
        if (pendingInvoices.length === 0) return

        setProcessing(true)

        for (const item of pendingInvoices) {
            setInvoices(prev => prev.map(inv =>
                inv.id === item.id ? { ...inv, status: 'processing' } : inv
            ))

            try {
                const formData = new FormData()
                formData.append('files', item.file)

                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                })

                const result = await response.json()
                const processed = result[0]

                setInvoices(prev => prev.map(inv =>
                    inv.id === item.id ? {
                        ...inv,
                        status: processed.status === 'success' ? 'done' : 'failed',
                        data: processed.data,
                        error: processed.error
                    } : inv
                ))

                await new Promise(r => setTimeout(r, 3000))

            } catch (err) {
                setInvoices(prev => prev.map(inv =>
                    inv.id === item.id ? { ...inv, status: 'failed', error: 'Network error' } : inv
                ))
            }
        }
        setProcessing(false)
    }

    const exportData = async (format) => {
        const payload = invoices
            .filter(inv => inv.status === 'done' && inv.data)
            .map(inv => ({ data: inv.data }))

        if (payload.length === 0) {
            alert("No processed invoices to export!")
            return
        }

        console.log("DEBUG EXPORT: Preparing export for", payload.length, "invoices");

        try {
            const response = await fetch('/api/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ invoices: payload, format })
            })

            if (response.ok) {
                const result = await response.json();
                console.log("DEBUG EXPORT: Preparation success, file_id:", result.file_id);

                // Two-Hop: Create a direct link to the download endpoint
                // We use a relative path so it goes through the Vite proxy, 
                // keeping the same origin and ensuring filenames are respected.
                const downloadUrl = `/api/download/${result.file_id}`;

                const link = document.createElement('a');
                link.href = downloadUrl;
                // No need to set .download here, server header Content-Disposition does it better
                document.body.appendChild(link);
                link.click();

                // Cleanup
                setTimeout(() => {
                    document.body.removeChild(link);
                }, 500);
            } else {
                alert("Export failed on server. Please try again.")
            }
        } catch (error) {
            console.error("Export error:", error);
            alert("Failed to export data. Check if server is running.")
        }
    }

    return (
        <div className="app-container">
            <header className="app-header animate-slide-down">
                <h1>GST Invoice Pro</h1>
                <p>Intelligent AI Assistant for Seamless GSTR-1 Compliance</p>
            </header>

            <main className="main-content">
                {/* Dashboard Summary */}
                <div className="dashboard-summary animate-fade-in">
                    <div className="summary-card glass-card">
                        <span className="summary-value">{stats.total}</span>
                        <span className="summary-label">Total Files</span>
                    </div>
                    <div className="summary-card glass-card">
                        <span className="summary-value">{stats.processed}</span>
                        <span className="summary-label">Processed</span>
                    </div>
                    <div className="summary-card glass-card">
                        <span className="summary-value">₹{stats.totalAmount.toLocaleString()}</span>
                        <span className="summary-label">Total Value</span>
                    </div>
                </div>

                {/* Upload Zone */}
                <div
                    className={`upload-section glass-card animate-fade-in ${isDragging ? 'dragging' : ''}`}
                    onDragOver={onDragOver}
                    onDragLeave={onDragLeave}
                    onDrop={onDrop}
                    onClick={() => document.getElementById('file-upload').click()}
                >
                    <span className="upload-icon">🚀</span>
                    <h2>Drop your invoices here</h2>
                    <p>Drag & Drop JPG, PNG, or PDF files or <span className="accent-text">Click to Browse</span></p>
                    <input type="file" multiple onChange={handleFileUpload} id="file-upload" hidden />
                </div>

                {/* Invoice List */}
                <div className="invoice-list animate-slide-up">
                    {invoices.map((inv) => (
                        <div key={inv.id} className="invoice-item glass-card animate-fade-in">
                            <div className="invoice-header">
                                <span className="filename">{inv.file.name}</span>
                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                    {inv.data?.gstin && <span className="gstin-badge">{inv.data.gstin}</span>}
                                    <span className={`status-badge ${inv.status}`}>
                                        {inv.status === 'processing' ? '⚡ PROCESSING' : inv.status.toUpperCase()}
                                    </span>
                                </div>
                            </div>

                            {inv.status === 'failed' && <p className="error-message" style={{ color: 'var(--error-color)' }}>⚠️ {inv.error}</p>}

                            {inv.data && (
                                <div className="invoice-details">
                                    <div className="detail">
                                        <label>Invoice Number</label>
                                        <span>{inv.data.invoice_number || 'N/A'}</span>
                                    </div>
                                    <div className="detail">
                                        <label>Total Amount</label>
                                        <span>₹{inv.data.total_amount?.toLocaleString() || '0'}</span>
                                    </div>
                                    <div className="detail">
                                        <label>Date</label>
                                        <span>{inv.data.date || 'N/A'}</span>
                                    </div>
                                    <div className="detail">
                                        <label>GST Rate</label>
                                        <span>{inv.data.rate ? `${inv.data.rate}%` : 'N/A'}</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                {/* Floating Actions */}
                {(invoices.length > 0) && (
                    <div className="actions animate-slide-up">
                        <button
                            className="btn-primary"
                            onClick={processAll}
                            disabled={processing || stats.pending === 0}
                        >
                            {processing ? '⚡ ANALYZING...' : '✨ START PROCESSING'}
                        </button>
                        <button
                            className="btn-secondary"
                            onClick={() => exportData('excel')}
                            disabled={processing || stats.processed === 0}
                        >
                            📥 EXPORT EXCEL
                        </button>
                        <button
                            className="btn-secondary"
                            onClick={() => exportData('csv')}
                            disabled={processing || stats.processed === 0}
                        >
                            📄 EXPORT CSV
                        </button>
                    </div>
                )}
            </main>

            <footer className="footer animate-fade-in" style={{ textAlign: 'center', marginTop: '4rem', opacity: 0.5 }}>
                <p>© 2026 GST Invoice Pro • High-Level AI Visual Reasoning</p>
            </footer>
        </div>
    )
}

export default App
