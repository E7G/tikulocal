package main

import (
	"gorm.io/gorm"
)

// 定义题目结构体
type Question struct {
	gorm.Model
	Type    string   `gorm:"index"`
	Text    string   `gorm:"index;unique"`
	Options []string `gorm:"type:text;serializer:json"`
	Answer  []string `gorm:"type:text;serializer:json"`
}
