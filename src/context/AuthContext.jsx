// src/context/AuthContext.jsx

import React, { createContext, useState, useContext, useMemo } from 'react';
import { jwtDecode } from 'jwt-decode';
import * as apiService from '../services/apiService';
import websocketService from '../services/websocketService';

const AuthContext = createContext(null);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [token, setToken] = useState(
        typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    );

    const [user, setUser] = useState(() => {
        if (typeof window === 'undefined') return null;
        const savedUser = localStorage.getItem('currentUser');
        try {
            return savedUser ? JSON.parse(savedUser) : null;
        } catch {
            localStorage.clear();
            return null;
        }
    });

    // ─── Derived role helpers ─────────────────────────────────────────────────
    // Single source of truth for role checks — use these everywhere instead of
    // repeating  user?.role === 'X'  across components.
    const isSuperAdmin  = useMemo(() => user?.role === 'SuperAdmin',  [user?.role]);
    const isAdmin       = useMemo(() => user?.role === 'Admin' || user?.role === 'SuperAdmin', [user?.role]);
    const isSiteManager = useMemo(() => user?.role === 'Site Manager', [user?.role]);

    const login = async (email, password) => {
        try {
            console.log("1. Sending Login Request...");
            const response = await apiService.login(email, password);
            console.log("2. Backend Response:", response);

            const { access_token } = response;

            if (!access_token) {
                throw new Error("No access token received from server.");
            }

            let decodedUser;
            try {
                decodedUser = jwtDecode(access_token);
                console.log("3. Decoded User:", decodedUser);
            } catch (decodeError) {
                console.error("Token Decode Error:", decodeError);
                throw new Error("Invalid token received from server.");
            }

            // Save BOTH keys to be safe (fallback key kept for backward compat)
            localStorage.setItem('access_token', access_token);
            localStorage.setItem('accessToken', access_token);
            localStorage.setItem('currentUser', JSON.stringify(decodedUser));

            setToken(access_token);
            setUser(decodedUser);

            console.log("4. Connecting WebSocket...");
            websocketService.connect();

            return decodedUser;
        } catch (error) {
            console.error("Login Flow Error:", error);
            logout();
            throw error;
        }
    };

    const logout = () => {
        websocketService.disconnect();
        apiService.logout();
        localStorage.removeItem('access_token');
        localStorage.removeItem('accessToken');
        localStorage.removeItem('currentUser');
        setToken(null);
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{
            token,
            user,
            isAuthenticated: !!token,
            // Role helpers — use these in components instead of repeating string checks
            isSuperAdmin,
            isAdmin,
            isSiteManager,
            login,
            logout,
        }}>
            {children}
        </AuthContext.Provider>
    );
};

export default AuthContext;
