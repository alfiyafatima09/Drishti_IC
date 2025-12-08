import { useCallback, useState } from 'react'
import type { RefObject } from 'react'
import { Upload, Image as ImageIcon } from 'lucide-react'
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
    <div className="rounded-2xl border-2 border-blue-300 bg-white p-5 shadow-2xl">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 shadow-lg">
          <ImageIcon className="h-6 w-6 text-white" />
        </div>
        <div>
          <h3 className="text-base font-bold text-slate-900">Upload IC Image</h3>
          <p className="text-sm font-medium text-purple-600">Alternative to live capture</p>
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
          'relative cursor-pointer rounded-xl border-3 border-dashed p-8 transition-all',
          'hover:border-purple-500 hover:bg-purple-50',
          isDragging &&
            'scale-105 border-purple-600 bg-gradient-to-br from-purple-50 to-pink-50 shadow-xl',
          !isDragging && 'border-purple-300 bg-gradient-to-br from-slate-50 to-purple-50',
          disabled && 'cursor-not-allowed opacity-50',
        )}
      >
        <div className="flex flex-col items-center justify-center">
          <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 shadow-lg">
            <Upload className="h-7 w-7 text-white" />
          </div>
          <p className="text-center text-base font-bold text-slate-900">
            {isDragging ? 'Drop image here' : 'Click or drag & drop'}
          </p>
          <p className="mt-2 text-sm font-medium text-purple-600">JPG, PNG (Max 10MB)</p>
        </div>
      </div>
    </div>
  )
}
