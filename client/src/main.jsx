import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './AuthContext.jsx';
import { ThemeProvider } from './ThemeContext.jsx';
import App from './App.jsx';
import './styles.css';
import './responsive.css';
import './dark-theme.css';
import './catalog.css';
import './dropdown.css';
import './premium-glass.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode><BrowserRouter><ThemeProvider><AuthProvider><App /></AuthProvider></ThemeProvider></BrowserRouter></React.StrictMode>
);
