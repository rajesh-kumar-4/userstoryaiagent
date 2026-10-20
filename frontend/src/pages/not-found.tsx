import { Link } from "react-router-dom";
import { buttonVariants } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center gap-4 py-24 text-center">
      <p className="text-sm font-semibold text-primary">404</p>
      <h1 className="text-2xl font-bold tracking-tight">Page not found</h1>
      <p className="max-w-md text-sm text-muted-foreground">The page you requested does not exist or has moved.</p>
      <Link to="/" className={buttonVariants()}>
        Back to dashboard
      </Link>
    </div>
  );
}
