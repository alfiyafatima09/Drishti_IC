import { useCallback, useState, RefObject } from 'react';
import { Upload, Image as ImageIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ImageUploadProps {
  onFileSelect: (file: File) => void;
  fileInputRef: RefObject<HTMLInputElement>;
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
    <div className="bg-white rounded-2xl shadow-2xl border-2 border-blue-300 p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 shadow-lg">
          <ImageIcon className="w-6 h-6 text-white" />
        </div>
        <div>
          <h3 className="text-base font-bold text-slate-900">Upload IC Image</h3>
          <p className="text-sm text-purple-600 font-medium">Alternative to live capture</p>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />

      <div
        onClick={handleClick}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className={cn(
          'relative rounded-xl border-3 border-dashed transition-all cursor-pointer p-8',
          'hover:border-purple-500 hover:bg-purple-50',
          isDragging && 'border-purple-600 bg-gradient-to-br from-purple-50 to-pink-50 scale-105 shadow-xl',
          !isDragging && 'border-purple-300 bg-gradient-to-br from-slate-50 to-purple-50',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <div className="flex flex-col items-center justify-center">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mb-3 shadow-lg">
            <Upload className="w-7 h-7 text-white" />
          </div>
          <p className="text-base font-bold text-slate-900 text-center">
            {isDragging ? 'Drop image here' : 'Click or drag & drop'}
          </p>
          <p className="text-sm text-purple-600 font-medium mt-2">JPG, PNG (Max 10MB)</p>
        </div>
      </div>
    </div>
  );
}

