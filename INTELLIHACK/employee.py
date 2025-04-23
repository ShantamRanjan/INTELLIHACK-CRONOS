
const express = require('express');
const axios = require('axios');
const cors = require('cors');
require('dotenv').config();

const app = express();
app.use(express.json());
app.use(cors());

const employees = [
  { id: 1, name: "Alice Smith", skills: ["javascript", "react", "node"], availability: { monday: [9, 17], tuesday: [9, 17], wednesday: [9, 17], thursday: [9, 17], friday: [9, 17] }, currentTask: null },
  { id: 2, name: "Bob Johnson", skills: ["python", "data analysis", "machine learning"], availability: { monday: [9, 17], tuesday: [9, 17], wednesday: [9, 17], thursday: [9, 17], friday: [9, 17] }, currentTask: "ML model training" },
  { id: 3, name: "Charlie Williams", skills: ["design", "ui", "photoshop"], availability: { monday: [9, 17], tuesday: [9, 17], wednesday: [9, 17], thursday: [9, 17], friday: [9, 17] }, currentTask: null },
  { id: 4, name: "Diana Lee", skills: ["java", "spring", "database"], availability: { monday: [9, 17], tuesday: [9, 17], wednesday: [9, 17], thursday: [13, 17], friday: [9, 17] }, currentTask: "Database optimization" },
  { id: 5, name: "Ethan Davis", skills: ["devops", "aws", "docker"], availability: { monday: [9, 17], tuesday: [9, 17], wednesday: [9, 17], thursday: [9, 17], friday: [9, 12] }, currentTask: null }
];

const tasks = [
  { id: 1, name: "Frontend bug fixes", description: "Fix UI bugs in the dashboard", skills: ["javascript", "react"], deadline: "2025-05-01", assigned: false, assignedTo: null },
  { id: 2, name: "Data pipeline setup", description: "Set up ETL pipeline for new data source", skills: ["python", "data analysis"], deadline: "2025-05-10", assigned: false, assignedTo: null },
  { id: 3, name: "Logo redesign", description: "Create new logo variants for rebranding", skills: ["design", "photoshop"], deadline: "2025-04-30", assigned: false, assignedTo: null }
];


const PERPLEXITY_API_KEY = process.env.PERPLEXITY_API_KEY;

async function queryPerplexity(query) {
try {
    const response = await axios.post(
    'https://api.perplexity.ai/chat/completions',
    {
        model: 'pplx-7b-online',
        messages: [{ role: 'user', content: query }],
        max_tokens: 1024
    },
    {
        headers: {
'Authorization': `Bearer ${PERPLEXITY_API_KEY}`,
        'Content-Type': 'application/json'
        }
    }
    );
    
    return response.data.choices[0].message.content;
} catch (error) {
    console.error('Error querying Perplexity API:', error);
    return 'Failed to get information from Perplexity.';
}
}


function isEmployeeAvailable(employee, day, hour) {
if (!employee.availability[day]) return false;
const [start, end] = employee.availability[day];
return hour >= start && hour < end && employee.currentTask === null;
}


function findSuitableEmployees(task, day, hour) {
return employees.filter(employee => {

    const hasRequiredSkills = task.skills.some(skill => 
    employee.skills.includes(skill)
    );
    
    // Check if employee is available
    const isAvailable = isEmployeeAvailable(employee, day, hour);
    
    return hasRequiredSkills && isAvailable;
});
}

// Routes
app.get('/api/employees', (req, res) => {
res.json(employees);
});

app.get('/api/tasks', (req, res) => {
res.json(tasks);
});

// Get available employees for a specific time
app.get('/api/available-employees', (req, res) => {
const { day, hour } = req.query;

if (!day || !hour) {
    return res.status(400).json({ error: 'Day and hour are required' });
}

const availableEmployees = employees.filter(employee => 
    isEmployeeAvailable(employee, day.toLowerCase(), parseInt(hour))
);

res.json(availableEmployees);
});

// Find the best employee for a task
app.post('/api/assign-task', async (req, res) => {
const { taskId, day, hour } = req.body;

if (!taskId || !day || !hour) {
    return res.status(400).json({ error: 'Task ID, day, and hour are required' });
}

const task = tasks.find(t => t.id === parseInt(taskId));
if (!task) {
    return res.status(404).json({ error: 'Task not found' });
}

const suitableEmployees = findSuitableEmployees(task, day.toLowerCase(), parseInt(hour));

if (suitableEmployees.length === 0) {
    return res.status(404).json({ error: 'No suitable employees available' });
}




const taskInfo = await queryPerplexity(`What are the best practices for assigning a task like "${task.description}" to team members?`);


const bestEmployee = suitableEmployees[0];


const employeeIndex = employees.findIndex(e => e.id === bestEmployee.id);
employees[employeeIndex].currentTask = task.name;

const taskIndex = tasks.findIndex(t => t.id === task.id);
tasks[taskIndex].assigned = true;
tasks[taskIndex].assignedTo = bestEmployee.id;

res.json({
    success: true,
    employee: bestEmployee,
    task: tasks[taskIndex],
    aiSuggestion: taskInfo
});
});


app.get('/api/get-recommendations', async (req, res) => {
  const { taskId } = req.query;
  
  if (!taskId) {
    return res.status(400).json({ error: 'Task ID is required' });
  }
  
  const task = tasks.find(t => t.id === parseInt(taskId));
  if (!task) {
    return res.status(404).json({ error: 'Task not found' });
  }
  
 
  const query = `Given a task "${task.description}" that requires skills in ${task.skills.join(', ')}, provide recommendations on the best assignment strategy and how to ensure timely completion by the deadline of ${task.deadline}.`;
  
  try {
    const recommendations = await queryPerplexity(query);
    res.json({
      success: true,
      task,
      recommendations
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to get recommendations' });
  }
});


app.get('/api/employee-insights/:id', async (req, res) => {
  const { id } = req.params;
  const employee = employees.find(e => e.id === parseInt(id));
  
  if (!employee) {
    return res.status(404).json({ error: 'Employee not found' });
  }
  

const query = `Provide insights on optimizing workload for an employee with skills in ${employee.skills.join(', ')}. Current task: ${employee.currentTask || 'None'}.`;

try {
    const insights = await queryPerplexity(query);
    res.json({
    success: true,
    employee,
    insights
    });
} catch (error) {
    res.status(500).json({ error: 'Failed to get insights' });
}
});


app.post('/api/complete-task', (req, res) => {
const { employeeId, taskId } = req.body;

if (!employeeId || !taskId) {
    return res.status(400).json({ error: 'Employee ID and Task ID are required' });
}

const employeeIndex = employees.findIndex(e => e.id === parseInt(employeeId));
if (employeeIndex === -1) {
    return res.status(404).json({ error: 'Employee not found' });
}

const taskIndex = tasks.findIndex(t => t.id === parseInt(taskId) && t.assignedTo === parseInt(employeeId));
if (taskIndex === -1) {
    return res.status(404).json({ error: 'Task not found or not assigned to this employee' });
}


employees[employeeIndex].currentTask = null;



tasks[taskIndex].completed = true;

res.json({
    success: true,
    employee: employees[employeeIndex],
    task: tasks[taskIndex]
});
});


const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
console.log(`Employee Assignment AI Agent running on port ${PORT}`);
});


/* 
<script>
  // Example of how to use the API from the frontend
async function getAvailableEmployees() {
    const day = document.getElementById('day').value;
    const hour = document.getElementById('hour').value;
    
    const response = await fetch(`/api/available-employees?day=${day}&hour=${hour}`);
    const employees = await response.json();
    
    displayEmployees(employees);
}

async function assignTask() {
    const taskId = document.getElementById('taskId').value;
    const day = document.getElementById('day').value;
    const hour = document.getElementById('hour').value;
    
    const response = await fetch('/api/assign-task', {
method: 'POST',
headers: {
        'Content-Type': 'application/json'
},
    body: JSON.stringify({ taskId, day, hour })
    });
    
    const result = await response.json();
    
    if (result.success) {
    alert(`Task assigned to ${result.employee.name}`);
      // Update UI
    } else {
    alert(result.error);
    }
}

function displayEmployees(employees) {
    const container = document.getElementById('employeeList');
    container.innerHTML = '';
    
    employees.forEach(employee => {
    const card = document.createElement('div');
    card.className = 'employee-card';
    card.innerHTML = `
        <h3>${employee.name}</h3>
        <p>Skills: ${employee.skills.join(', ')}</p>
        <button onclick="getEmployeeInsights(${employee.id})">Get Insights</button>
    `;
    container.appendChild(card);
    });
}

async function getEmployeeInsights(id) {
    const response = await fetch(`/api/employee-insights/${id}`);
    const data = await response.json();
    
    // Display insights in a modal or panel
    showInsightsModal(data);
}

function showInsightsModal(data) {
    // Implementation for displaying insights
    const modal = document.getElementById('insightsModal');
    const content = document.getElementById('insightsContent');
    
    content.innerHTML = `
      <h2>${data.employee.name}</h2>
      <p>${data.insights}</p>
    `;
    
    modal.style.display = 'block';
  }
</script>
*/