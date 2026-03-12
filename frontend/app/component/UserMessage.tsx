interface UserMessageProps {
  content: string;
}

export default function UserMessage({ content }: UserMessageProps) {
  return (
    <div className="flex justify-end mb-8">
      <div className="max-w-[85%] sm:max-w-[70%] px-5 py-3.5 rounded-[2rem] rounded-tr-md bg-blue-600 text-white shadow-lg shadow-blue-600/10">
        <p className="text-[15px] leading-relaxed">{content}</p>
      </div>
    </div>
  );
}
