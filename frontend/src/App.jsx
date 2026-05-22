import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "./contexts/AuthContext";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Property from "./pages/Property";
import Favorites from "./pages/Favorites";
import Admin from "./pages/Admin";
import CreateListing from "./pages/CreateListing";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Navbar />
        <main className="max-w-6xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/listings/:id" element={<Property />} />
            <Route path="/favorites" element={<Favorites />} />
            <Route path="/add-property" element={<CreateListing />} />
            <Route path="/admin" element={<Admin />} />
          </Routes>
        </main>
        <Toaster position="top-right" />
      </BrowserRouter>
    </AuthProvider>
  );
}
