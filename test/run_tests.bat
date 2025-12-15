@echo off
echo Running parser tests...
cd /d d:\Documents\GitHub\tikulocal

echo Running verify_fix test...
copy test\verify_fix.go verify_fix_temp.go >nul
go run verify_fix_temp.go parser.go models.go
del verify_fix_temp.go

echo.
echo Running test_parser test...
copy test\test_parser.go test_parser_temp.go >nul
go run test_parser_temp.go parser.go models.go
del test_parser_temp.go

echo.
echo All tests completed!