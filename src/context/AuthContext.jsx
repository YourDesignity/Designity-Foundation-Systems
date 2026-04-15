// src/context/AuthContext.js

import React, { createContext, useState, useContext } from 'react';
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

    const login = async (email, password) => {
        try {
            console.log("1. Sending Login Request...");
            const response = await apiService.login(email, password);
            console.log("2. Backend Response:", response);

            const { access_token } = response;
            
            if (!access_token) {
                throw new Error("No access token received from server.");
            }

            // Decode Token
            let decodedUser;
            try {
                decodedUser = jwtDecode(access_token);
                console.log("3. Decoded User:", decodedUser);
            } catch (decodeError) {
                console.error("Token Decode Error:", decodeError);
                throw new Error("Invalid token received from server.");
            }

            // --- FIX: Save BOTH keys to be safe ---
            localStorage.setItem('access_token', access_token);
            localStorage.setItem('accessToken', access_token); // Fallback key
            localStorage.setItem('currentUser', JSON.stringify(decodedUser));
            
            setToken(access_token);
            setUser(decodedUser);

            // Connect WebSocket AFTER token is saved
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
        // Disconnect WebSocket BEFORE clearing token
        websocketService.disconnect();

        apiService.logout();
        localStorage.removeItem('access_token');
        localStorage.removeItem('accessToken'); // Remove fallback key too
        localStorage.removeItem('currentUser');
        setToken(null);
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{
            token,
            user,
            isAuthenticated: !!token,
            login,
            logout,
        }}>
            {children}
        </AuthContext.Provider>
    );
};

export default AuthContext;