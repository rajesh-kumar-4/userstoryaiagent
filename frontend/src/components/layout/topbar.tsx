import { useState } from "react";
import { Moon, Radio, Sun, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input, Label } from "@/components/ui/input";
import { RepoSelect } from "@/components/common/repo-select";
import { useAppState } from "@/state/app-state";

export function ApiKeyDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { apiKey, setApiKey } = useAppState();
  const [value, setValue] = useState(apiKey);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="API key"
      description="The key is stored in this browser's localStorage and sent as the X-API-Key header."
    >
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          setApiKey(value);
          onClose();
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="api-key">Key</Label>
          <Input
            id="api-key"
            type="password"
            autoComplete="off"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder="Paste the key issued by the administrator"
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setValue("");
              setApiKey("");
            }}
          >
            Clear
          </Button>
          <Button type="submit">Save key</Button>
        </div>
      </form>
    </Dialog>
  );
}

export function Topbar() {
  const { theme, toggleTheme, live, setLive, apiKey } = useAppState();
  const [keyOpen, setKeyOpen] = useState(false);

  return (
    <header className="sticky top-0 z-20 flex flex-wrap items-center gap-3 border-b border-border bg-background/85 px-4 py-3 backdrop-blur md:px-6">
      <div className="ml-24 flex min-w-0 flex-1 items-center gap-3 md:ml-0">
        <RepoSelect />
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant={live ? "default" : "outline"}
          size="sm"
          onClick={() => setLive(!live)}
          aria-pressed={live}
          title="Poll dashboards and events every 15 seconds"
        >
          <Radio className={live ? "animate-pulse" : ""} aria-hidden="true" />
          {live ? "Live" : "Paused"}
        </Button>
        <Button variant="outline" size="icon" onClick={toggleTheme} aria-label="Toggle dark mode">
          {theme === "dark" ? <Sun /> : <Moon />}
        </Button>
        <Button variant="outline" size="sm" onClick={() => setKeyOpen(true)}>
          <KeyRound aria-hidden="true" />
          {apiKey ? "API key set" : "Set API key"}
        </Button>
      </div>
      <ApiKeyDialog open={keyOpen} onClose={() => setKeyOpen(false)} />
    </header>
  );
}
