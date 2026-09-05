import { useQuery } from "@tanstack/react-query";
import * as React from "react";

import { Select } from "@/components/ui/select";
import { listCPSE } from "@/services/cpse";

interface OrganizationSelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "children"> {
  includeAllOption?: boolean;
  includeInactive?: boolean;
}

/**
 * Single source of truth for "which organizations exist" in the UI - every
 * dropdown that needs an org list renders this instead of a static array, so
 * a brand-new organization shows up everywhere the moment it's created.
 */
export const OrganizationSelect = React.forwardRef<HTMLSelectElement, OrganizationSelectProps>(
  ({ includeAllOption = false, includeInactive = true, ...props }, ref) => {
    const { data, isLoading } = useQuery({ queryKey: ["cpse"], queryFn: listCPSE });
    const options = (data ?? []).filter((org) => includeInactive || org.is_active);

    return (
      <Select ref={ref} {...props}>
        {includeAllOption && <option value="">All Organizations</option>}
        {!includeAllOption && !props.value && <option value="">{isLoading ? "Loading..." : "Select Organization"}</option>}
        {options.map((org) => (
          <option key={org.id} value={org.id} disabled={!org.is_active}>
            {org.code} — {org.name}
            {!org.is_active ? " (Inactive)" : ""}
          </option>
        ))}
      </Select>
    );
  }
);
OrganizationSelect.displayName = "OrganizationSelect";
