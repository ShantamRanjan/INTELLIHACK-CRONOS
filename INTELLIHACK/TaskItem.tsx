import React, { useState } from 'react';
import { Check, AlertCircle, Clock, Circle, MoreVertical, Trash, Edit } from 'lucide-react';

interface Task {
  id: number;
  title: string;
  description?: string;
  completed: boolean;
  priority: 'high' | 'medium' | 'low';
  date: string;
}

interface TaskItemProps {
  task: Task;
  onToggle: () => void;
  onDelete: () => void;
}

const TaskItem: React.FC<TaskItemProps> = ({ task, onToggle, onDelete }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [showDescription, setShowDescription] = useState(false);

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'high':
        return <AlertCircle className="w-4 h-4 text-red-500 dark:text-red-400" />;
      case 'medium':
        return <Clock className="w-4 h-4 text-amber-500 dark:text-amber-400" />;
      case 'low':
        return <Circle className="w-4 h-4 text-blue-500 dark:text-blue-400" />;
      default:
        return null;
    }
  };

  return (
    <div className={`p-4 transition-colors duration-200 hover:bg-gray-50 dark:hover:bg-gray-750 ${
      task.completed ? 'bg-gray-50 dark:bg-gray-850' : ''
    }`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-grow min-w-0" onClick={() => task.description && setShowDescription(!showDescription)}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggle();
            }}
            className={`flex-shrink-0 w-5 h-5 mt-1 rounded-full border ${
              task.completed
                ? 'bg-green-500 border-green-500 dark:bg-green-600 dark:border-green-600 flex items-center justify-center'
                : 'border-gray-300 dark:border-gray-600'
            }`}
          >
            {task.completed && <Check className="w-3 h-3 text-white" />}
          </button>
          
          <div className="flex flex-col flex-grow min-w-0">
            <div className="flex items-start">
              <span
                className={`font-medium mr-2 ${
                  task.completed
                    ? 'text-gray-500 dark:text-gray-400 line-through'
                    : 'text-gray-900 dark:text-white'
                }`}
              >
                {task.title}
              </span>
            </div>
            
            <div className="flex items-center mt-1 space-x-2">
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {new Date(task.date).toLocaleDateString()}
              </span>
              <div className="flex items-center" title={`Priority: ${task.priority}`}>
                {getPriorityIcon(task.priority)}
              </div>
              {task.description && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowDescription(!showDescription);
                  }}
                  className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                >
                  {showDescription ? 'Hide details' : 'Show details'}
                </button>
              )}
            </div>
            
            {showDescription && task.description && (
              <div className="mt-2 text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-750 p-2 rounded">
                {task.description}
              </div>
            )}
          </div>
        </div>
        
        <div className="relative">
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="p-1 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <MoreVertical className="w-4 h-4" />
          </button>
          
          {isMenuOpen && (
            <div className="absolute right-0 mt-1 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg py-1 z-10 ring-1 ring-black ring-opacity-5">
              <button
                className="flex w-full items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                onClick={() => {
                  setIsMenuOpen(false);
                  console.log('Edit task:', task.id);
                }}
              >
                <Edit className="w-4 h-4 mr-2" />
                Edit Task
              </button>
              <button
                className="flex w-full items-center px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                onClick={() => {
                  setIsMenuOpen(false);
                  onDelete();
                }}
              >
                <Trash className="w-4 h-4 mr-2" />
                Delete Task
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TaskItem;