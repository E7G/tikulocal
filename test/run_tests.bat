@echo off
echo Running parser tests...
cd /d d:\Documents\GitHub\tikulocal
go run test\verify_fix.go parser.go models.go
echo.
echo Running test_parser tests...
go run test\test_parser.go parser.go models.go
echo.
echo All tests completed!