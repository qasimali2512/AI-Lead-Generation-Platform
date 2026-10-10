import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

import "./NotFoundPage.css";

function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <main className="not-found-page">
      <div className="not-found-card">
        <span>404</span>

        <h1>
          Page not found
        </h1>

        <p>
          The page you're looking for doesn't
          exist or may have moved.
        </p>

        <button
          type="button"
          onClick={() => navigate("/")}
        >
          <ArrowLeft size={17} />
          Go home
        </button>
      </div>
    </main>
  );
}

export default NotFoundPage;