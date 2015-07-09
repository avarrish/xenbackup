#!/usr/bin/perl

use strict;
use warnings;
use feature qw(switch say);

my $file = "/path/to/your/backups/backup.log";
open (FH, "< $file") or die "Can't open $file for read: $!";

my $age = -M FH;

if ($age > 6) {
	print "Critical - Logfile too old. ($age)"; exit(2); 
}
if ($age > 4) {
	print "Warning - Logfile old. ($age)"; exit(1); 
}

while (<FH>) {
    (my $timestamp, my $type, my $message) = split(' - ');

    if ($type eq 'ERROR' ) {
	$message =~ s/^\s+|\s+$//g ; 
	print "Critical - $message ($timestamp)"; exit(2); 
    }
}
close FH or die "Cannot close $file: $!";

print "OK - No problems found."; exit(0); 
