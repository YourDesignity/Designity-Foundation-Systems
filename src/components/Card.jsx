import React from 'react'
import { BiLogoHtml5 , BiLogoAndroid , BiBuilding } from "react-icons/bi";
const courses = [
    {
        title: 'Inspect Budget',
        icon: <BiLogoHtml5 />,
    },
    {
        title: 'Invertory',
        duration:'2 Hours',
        icon: <BiLogoAndroid />,
    },
    {
        title: 'Products',
        duration:'3 Hours',
        icon: <BiBuilding />,
    },
];



const Card = () => {
  return (
    <div className='card--container' >
        {courses.map((item) => (
            <div className='card'>
                <div className="card--cover">
                {item.icon}</div>
                <div className="card--title">
                <h2>{item.title}</h2>
                </div>
            </div>
        ))}
    </div>
  )
}

export default Card