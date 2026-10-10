import {
  ToastContainer,
} from "react-toastify";

import {
  AuthProvider,
} from "./context/AuthContext";

import AppRouter from "./routes/AppRouter";

import "./App.css";
import "react-toastify/dist/ReactToastify.css";

function App() {
  return (
    <AuthProvider>
      <div className="app">
        <AppRouter />
      </div>

      <ToastContainer
        position="bottom-right"
        autoClose={3500}
        newestOnTop
        closeOnClick
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />
    </AuthProvider>
  );
}

export default App;