import { useCallback, useState, RefObject } from 'react';
import { Upload, ImageIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ImageUploadProps {
  onFileSelect: (file: File) => void;
  fileInputRef: RefObject<HTMLInputElement | null>;
  disabled?: boolean;
}

export function ImageUpload({ onFileSelect, fileInputRef, disabled }: ImageUploadProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) setIsDragging(true);
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (disabled) return;

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type.startsWith('image/')) {
        onFileSelect(file);
      }
    }
  }, [onFileSelect, disabled]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileSelect(files[0]);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [onFileSelect, fileInputRef]);

  const handleClick = useCallback(() => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  }, [fileInputRef, disabled]);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 md:p-5">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
          <ImageIcon className="w-5 h-5 text-slate-600" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Upload Image</h3>
          <p className="text-xs text-slate-500">Or drag and drop a file</p>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Drop Zone */}
      <div
        onClick={handleClick}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className={cn(
          'relative rounded-lg border-2 border-dashed transition-all cursor-pointer',
          'flex flex-col items-center justify-center py-8 px-4',
          isDragging && 'border-blue-500 bg-blue-50',
          !isDragging && 'border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-slate-100',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <div className={cn(
          'w-12 h-12 rounded-full flex items-center justify-center mb-3 transition-colors',
          isDragging ? 'bg-blue-100' : 'bg-slate-200'
        )}>
          <Upload className={cn('w-5 h-5', isDragging ? 'text-blue-600' : 'text-slate-500')} />
        </div>
        <p className="text-sm font-medium text-slate-700 text-center">
          {isDragging ? 'Drop image here' : 'Click to browse or drag & drop'}
        </p>
        <p className="text-xs text-slate-400 mt-1">PNG, JPG up to 10MB</p>
      </div>
    </div>
  );
}
