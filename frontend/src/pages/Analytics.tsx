import { useQuery } from "@tanstack/react-query";

import { SimpleBarChart } from "@/charts/SimpleBarChart";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getClassificationDistribution, getCommonCodeAdoption, getCpseComparison, getHarmonizationTrends, getMaterialQuality } from "@/services/analytics";

export default function Analytics() {
  const { data: classification } = useQuery({ queryKey: ["analytics", "classification"], queryFn: getClassificationDistribution });
  const { data: cpseComparison } = useQuery({ queryKey: ["analytics", "cpse-comparison"], queryFn: getCpseComparison });
  const { data: adoption } = useQuery({ queryKey: ["analytics", "common-code-adoption"], queryFn: getCommonCodeAdoption });
  const { data: quality } = useQuery({ queryKey: ["analytics", "material-quality"], queryFn: getMaterialQuality });
  const { data: trends } = useQuery({ queryKey: ["analytics", "harmonization-trends"], queryFn: getHarmonizationTrends });

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumbs={[{ label: "Analytics" }, { label: "Material Master Analytics" }]}
        title="Material Master Analytics"
        subtitle="Deeper insight into harmonization performance across the National Material Master."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>CPSE Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <SimpleBarChart data={cpseComparison ?? []} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Classification Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <SimpleBarChart data={classification ?? []} color="#4a3aa7" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Common Code Adoption (by decision status)</CardTitle>
          </CardHeader>
          <CardContent>
            <SimpleBarChart data={adoption ?? []} color="#138808" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Material Quality</CardTitle>
          </CardHeader>
          <CardContent>
            <SimpleBarChart data={quality ?? []} color="#eb6834" />
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Harmonization Trend (mappings created per month)</CardTitle>
          </CardHeader>
          <CardContent>
            <SimpleBarChart data={trends ?? []} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
