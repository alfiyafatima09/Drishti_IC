import { useCallback, useState, RefObject } from 'react'
import { Upload, ImageIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ImageUploadProps {
  onFileSelect: (file: File) => void
  fileInputRef: RefObject<HTMLInputElement | null>
  disabled?: boolean
}

export function ImageUpload({ onFileSelect, fileInputRef, disabled }: ImageUploadProps) {
  const [isDragging, setIsDragging] = useState(false)

  const handleDragEnter = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      if (!disabled) setIsDragging(true)
    },
    [disabled],
  )

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)

      if (disabled) return

      const files = e.dataTransfer.files
      if (files && files.length > 0) {
        const file = files[0]
        if (file.type.startsWith('image/')) {
          onFileSelect(file)
        }
      }
    },
    [onFileSelect, disabled],
  )

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files && files.length > 0) {
        onFileSelect(files[0])
      }
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    },
    [onFileSelect, fileInputRef],
  )

  const handleClick = useCallback(() => {
    if (!disabled) {
      fileInputRef.current?.click()
    }
  }, [fileInputRef, disabled])

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:p-5">
      {/* Header */}
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100">
          <ImageIcon className="h-5 w-5 text-slate-600" />
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
          'relative cursor-pointer rounded-lg border-2 border-dashed transition-all',
          'flex flex-col items-center justify-center px-4 py-8',
          isDragging && 'border-blue-500 bg-blue-50',
          !isDragging && 'border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-slate-100',
          disabled && 'cursor-not-allowed opacity-50',
        )}
      >
        <div
          className={cn(
            'mb-3 flex h-12 w-12 items-center justify-center rounded-full transition-colors',
            isDragging ? 'bg-blue-100' : 'bg-slate-200',
          )}
        >
          <Upload className={cn('h-5 w-5', isDragging ? 'text-blue-600' : 'text-slate-500')} />
        </div>
        <p className="text-center text-sm font-medium text-slate-700">
          {isDragging ? 'Drop image here' : 'Click to browse or drag & drop'}
        </p>
        <p className="mt-1 text-xs text-slate-400">PNG, JPG up to 10MB</p>
      </div>
    </div>
  )
}
