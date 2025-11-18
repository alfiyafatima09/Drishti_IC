/**
 * Analysis Results Component
 * Displays verification results after IC scan
 */

'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Camera, CheckCircle2, XCircle } from 'lucide-react';
import { formatPercentage } from '@/utils/format';

interface AnalysisResultsProps {
  result: any | null;
  onViewDetails?: () => void;
}

export function AnalysisResults({ result, onViewDetails }: AnalysisResultsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Analysis Results</CardTitle>
        <CardDescription>Verification results will appear here</CardDescription>
      </CardHeader>
      <CardContent>
        {result ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              {result.is_genuine ? (
                <>
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <span className="font-semibold text-green-600">Genuine</span>
                </>
              ) : (
                <>
                  <XCircle className="h-5 w-5 text-red-600" />
                  <span className="font-semibold text-red-600">Counterfeit</span>
                </>
              )}
            </div>

            {result.confidence !== undefined && (
              <div>
                <p className="text-sm text-muted-foreground">Confidence</p>
                <p className="text-2xl font-bold">
                  {formatPercentage(result.confidence, 1)}
                </p>
              </div>
            )}

            {result.part_number && (
              <div>
                <p className="text-sm text-muted-foreground">Part Number</p>
                <p className="font-mono">{result.part_number}</p>
              </div>
            )}

            {result.manufacturer && (
              <div>
                <p className="text-sm text-muted-foreground">Manufacturer</p>
                <p>{result.manufacturer}</p>
              </div>
            )}

            {result.verification_id && onViewDetails && (
              <Button onClick={onViewDetails} className="w-full">
                View Detailed Results
              </Button>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Camera className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No analysis results yet</p>
            <p className="text-sm">Upload an image to get started</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

