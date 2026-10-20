import { Label, Select } from "@/components/ui/input";

export interface RefOption {
  value: string;
  label: string;
}

/** Native select for picking a branch or ref. An empty value means "not chosen". */
export function RefSelect({
  id,
  label,
  value,
  onChange,
  options,
  placeholder = "Select a ref",
  allowEmpty = false,
  disabled,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: RefOption[];
  placeholder?: string;
  allowEmpty?: boolean;
  disabled?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Select id={id} value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled}>
        {(!value || allowEmpty) && <option value="">{allowEmpty ? "None" : placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
    </div>
  );
}
