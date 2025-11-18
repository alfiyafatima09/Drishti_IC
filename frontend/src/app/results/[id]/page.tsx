'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { apiRequest } from '@/api/client';
import { API_ENDPOINTS } from '@/lib/config';
import { useToast } from '@/hooks/use-toast';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle2, XCircle, Loader2, ArrowLeft, Download } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Badge } from '@/components/ui/badge';

export default function ResultsPage() {
  const params = useParams();
  const id = params.id as string;
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  const router = useRouter();

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const data = await apiRequest<any>(API_ENDPOINTS.verificationResult(Number(id)));
        setResult(data);
      } catch (error: any) {
        toast({
          title: 'Error',
          description: error.message || 'Failed to load results',
          variant: 'destructive',
        });
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchResult();
    }
  }, [id, toast]);

  if (loading) {
    return (
      <div className="container mx-auto p-6 flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!result) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">Result not found</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="outline" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Verification Results</h1>
            <p className="text-muted-foreground">Detailed analysis report</p>
          </div>
        </div>
        <Button variant="outline">
          <Download className="h-4 w-4 mr-2" />
          Export Report
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Verification Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                {result.is_genuine ? (
                  <>
                    <CheckCircle2 className="h-12 w-12 text-green-600" />
                    <div>
                      <h3 className="text-2xl font-bold text-green-600">Genuine</h3>
                      <p className="text-muted-foreground">Component verified as authentic</p>
                    </div>
                  </>
                ) : (
                  <>
                    <XCircle className="h-12 w-12 text-red-600" />
                    <div>
                      <h3 className="text-2xl font-bold text-red-600">Counterfeit</h3>
                      <p className="text-muted-foreground">Component failed verification</p>
                    </div>
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Component Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {result.part_number && (
                <div>
                  <p className="text-sm text-muted-foreground">Part Number</p>
                  <p className="font-mono text-lg">{result.part_number}</p>
                </div>
              )}
              {result.manufacturer && (
                <div>
                  <p className="text-sm text-muted-foreground">Manufacturer</p>
                  <p className="text-lg">{result.manufacturer}</p>
                </div>
              )}
              {result.package_type && (
                <div>
                  <p className="text-sm text-muted-foreground">Package Type</p>
                  <p className="text-lg">{result.package_type}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {result.metrics && (
            <Card>
              <CardHeader>
                <CardTitle>Verification Metrics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {result.metrics.confidence && (
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-sm">Confidence</span>
                      <span className="text-sm font-medium">
                        {(result.metrics.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-2">
                      <div
                        className="bg-primary h-2 rounded-full"
                        style={{ width: `${result.metrics.confidence * 100}%` }}
                      />
                    </div>
                  </div>
                )}
                {result.metrics.logo_match_score && (
                  <div>
                    <p className="text-sm text-muted-foreground">Logo Match Score</p>
                    <p className="text-lg">{(result.metrics.logo_match_score * 100).toFixed(1)}%</p>
                  </div>
                )}
                {result.metrics.font_match_score && (
                  <div>
                    <p className="text-sm text-muted-foreground">Font Match Score</p>
                    <p className="text-lg">{(result.metrics.font_match_score * 100).toFixed(1)}%</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {result.issues && result.issues.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Detected Issues</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {result.issues.map((issue: string, index: number) => (
                    <li key={index} className="flex items-start gap-2">
                      <XCircle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                      <span>{issue}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Analysis Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {result.created_at && (
                <div>
                  <p className="text-sm text-muted-foreground">Analysis Date</p>
                  <p>{new Date(result.created_at).toLocaleString()}</p>
                </div>
              )}
              {result.verification_id && (
                <div>
                  <p className="text-sm text-muted-foreground">Verification ID</p>
                  <p className="font-mono text-xs">{result.verification_id}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {result.image_url && (
            <Card>
              <CardHeader>
                <CardTitle>Analyzed Image</CardTitle>
              </CardHeader>
              <CardContent>
                <img
                  src={result.image_url}
                  alt="Analyzed IC"
                  className="w-full rounded-lg"
                />
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

