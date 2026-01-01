import React from 'react';
import Editor from '@monaco-editor/react';

interface CodeEditorProps {
  language: string;
  value: string;
  onChange: (val: string) => void;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({ language, value, onChange }) => {
  return (
    <div className="w-full h-full border rounded-lg overflow-hidden">
      <Editor
        height="100%"
        theme="vs-dark"
        defaultLanguage={language}
        value={value}
        onChange={(val) => onChange(val ?? '')}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          scrollBeyondLastLine: false,
          automaticLayout: true,
        }}
      />
    </div>
  );
};
