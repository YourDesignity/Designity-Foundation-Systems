import React from 'react'
import '../styles/teacherList.css'
import Image1 from '../assets/image1.png'

const teachers = [
  {
    image: Image1,
    name: 'Shivagiri',
    duration: '8 Hours Shift',
    cost: '100',
  },
    {
    image: Image1,
    name: 'Deepak',
    duration: '24 Hours Shift',
    cost: '100',
  },
  {
    image: Image1,
    name: 'Ajmal k',
    duration: '11 Hours Shift',
    cost: '100',
  },
  {
    image: Image1,
    name: 'Abhijith',
    duration: '12 Hours Shift',
    cost: '100',
  },

];


//  Data


const TeacherList = () => {
  return (
    <div className='teacher--list' >
      <div className="list--header">
        <h2>Employees</h2>
        <select> 
          <option value="english">Mrng Shift</option>
          <option value="hindi">Eve Shift</option>
          <option value="english">Night Shift</option>
        </select>
      </div>
      <div className="list--container">
        {teachers.map((teacher) => (
        <div className='list'>
          <div className="teacher--detail">
          <img src={teacher.image} alt={teacher.name} />
          <h2>{teacher.name}</h2>
          </div>
          <span>{teacher.duration}</span>
          <span>${teacher.cost}/hr</span>
          <span className='teacher--todo'>::</span>
        </div>
        ))}
      </div>
    </div>

  )
}

export default TeacherList