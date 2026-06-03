import { Dialog, DialogPanel, DialogTitle, Transition, TransitionChild } from "@headlessui/react";
import { X } from "lucide-react";
import { Fragment } from "react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  size?: "sm" | "md" | "lg";
}

const sizeMap = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
};

/**
 * 通用模态对话框组件
 * @param open 是否显示
 * @param onClose 关闭回调
 * @param title 标题
 * @param children 内容
 * @param size 尺寸，默认 md
 */
export default function Modal({ open, onClose, title, children, size = "md" }: ModalProps) {
  return (
    <Transition show={open} as={Fragment}>
      <Dialog onClose={onClose} className="relative z-50">
        <TransitionChild
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" />
        </TransitionChild>

        <div className="fixed inset-0 flex items-center justify-center p-4">
          <TransitionChild
            as={Fragment}
            enter="ease-out duration-200"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-150"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <DialogPanel className={`glass-card w-full ${sizeMap[size]} p-0`}>
              <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
                <DialogTitle className="text-ink-100 text-base font-medium">
                  {title}
                </DialogTitle>
                <button
                  onClick={onClose}
                  className="text-ink-400 hover:text-ink-100 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="px-5 py-4">
                {children}
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </Dialog>
    </Transition>
  );
}
