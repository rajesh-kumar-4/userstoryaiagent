import type { ReactNode } from "react";
import { AlertTriangle, Inbox, Loader2, ShieldAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { useAppState } from "@/state/app-state";

export function LoadingState({ rows = 3, label = "Loading" }: { rows?: number; label?: string }) {
  return (
    <div className="space-y-3" role="status" aria-label={label}>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-12 w-full" />
      ))}
      <span className="sr-only">{label}</span>
    </div>
  );
}

export function InlineSpinner({ label = "Working" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-muted-foreground" role="status">
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      {label}
    </span>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { apiKey } = useAppState();
  const authProblem = error instanceof ApiError && error.isAuthError;
  const message = error instanceof Error ? error.message : "An unexpected error occurred";
  const hint = !apiKey
    ? "No API key is set. Use Set API key in the top bar."
    : "The stored key is rejected or lacks permission for this action. Update the key from the top bar.";

  return (
    <Alert variant="destructive" className="flex flex-col gap-3">
      <div className="flex items-start gap-3">
        {authProblem ? (
          <ShieldAlert className="mt-0.5 size-5" aria-hidden="true" />
        ) : (
          <AlertTriangle className="mt-0.5 size-5" aria-hidden="true" />
        )}
        <div className="min-w-0">
          <AlertTitle>{authProblem ? "Access denied" : "Request failed"}</AlertTitle>
          <AlertDescription className="break-words">{message}</AlertDescription>
          {authProblem && <AlertDescription className="mt-1">{hint}</AlertDescription>}
        </div>
      </div>
      {onRetry && (
        <button type="button" onClick={onRetry} className="self-start text-sm font-medium underline underline-offset-4">
          Try again
        </button>
      )}
    </Alert>
  );
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
        <Inbox className="size-8 text-muted-foreground" aria-hidden="true" />
        <p className="font-medium">{title}</p>
        {description && <p className="max-w-md text-sm text-muted-foreground">{description}</p>}
        {action}
      </CardContent>
    </Card>
  );
}

export function NeedsRepository({ children }: { children?: ReactNode }) {
  return (
    <EmptyState
      title="Select a repository"
      description="Choose a repository in the top bar to use this page."
      action={children}
    />
  );
}
